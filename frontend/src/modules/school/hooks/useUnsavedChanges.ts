import { useLayoutEffect } from 'react';

// Register before BrowserRouter subscribes so a rejected Back event cannot unmount
// the dirty form before its navigation guard receives the event.
let activeHistoryGuard: { index: unknown; restoring: boolean } | null = null;
if (typeof window !== 'undefined') window.addEventListener('popstate', event => {
    const guard = activeHistoryGuard;
    if (!guard) return;
    if (guard.restoring) { guard.restoring = false; event.stopImmediatePropagation(); return; }
    const nextIndex = event.state?.idx;
    if (typeof guard.index !== 'number' || typeof nextIndex !== 'number' || guard.index === nextIndex) return;
    if (!window.confirm('Discard your unsaved changes?')) {
        event.stopImmediatePropagation(); guard.restoring = true;
        window.history.go(guard.index - nextIndex);
    }
}, true);

/** Protect full-page exits and in-app links while a School form has local edits. */
export function useUnsavedChanges(dirty: boolean) {
    useLayoutEffect(() => {
        if (!dirty) return;
        const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
        const click = (event: MouseEvent) => {
            const link = (event.target as Element)?.closest?.('a[href]');
            if (!link || event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            if (!window.confirm('Discard your unsaved changes?')) {
                event.preventDefault(); event.stopPropagation();
            }
        };
        const guard = { index: window.history.state?.idx, restoring: false };
        activeHistoryGuard = guard;
        window.addEventListener('beforeunload', unload);
        document.addEventListener('click', click, true);
        return () => { if (activeHistoryGuard === guard) activeHistoryGuard = null; window.removeEventListener('beforeunload', unload); document.removeEventListener('click', click, true); };
    }, [dirty]);
}
