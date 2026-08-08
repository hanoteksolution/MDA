const FAV_KEY = "mda.hub.favorites";
const REC_KEY = "mda.hub.recents";
const MAX_RECENTS = 12;

export interface HubRecent {
  code: string;
  visitedAt: number;
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function loadHubFavorites(): string[] {
  const codes = readJson<string[]>(FAV_KEY, []);
  return Array.isArray(codes) ? codes.filter((c) => typeof c === "string") : [];
}

export function saveHubFavorites(codes: string[]): void {
  localStorage.setItem(FAV_KEY, JSON.stringify(codes));
}

export function toggleHubFavorite(code: string): string[] {
  const current = loadHubFavorites();
  const next = current.includes(code) ? current.filter((c) => c !== code) : [...current, code];
  saveHubFavorites(next);
  return next;
}

export function loadHubRecents(): HubRecent[] {
  const recents = readJson<HubRecent[]>(REC_KEY, []);
  if (!Array.isArray(recents)) return [];
  return recents.filter((r) => r && typeof r.code === "string" && typeof r.visitedAt === "number");
}

export function recordHubVisit(code: string): HubRecent[] {
  if (!code) return loadHubRecents();
  const now = Date.now();
  const next = [{ code, visitedAt: now }, ...loadHubRecents().filter((r) => r.code !== code)].slice(
    0,
    MAX_RECENTS
  );
  localStorage.setItem(REC_KEY, JSON.stringify(next));
  return next;
}

export function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(ts).toLocaleDateString();
}

export function greetingForHour(date = new Date()): string {
  const h = date.getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}
