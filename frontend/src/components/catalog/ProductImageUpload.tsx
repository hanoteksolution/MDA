import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, X, Loader2, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { resolveProductImageUrl } from "@/config/api";
import { cn } from "@/utils/cn";

const ACCEPT = "image/jpeg,image/png,image/webp,image/gif";
const MAX_MB = 5;

interface ProductImageUploadProps {
  value?: string;
  previewUrl?: string;
  name?: string;
  sku?: string;
  categoryName?: string;
  onChange: (url: string) => void;
  onPreviewChange?: (preview: string | null) => void;
  onUpload: (file: File) => Promise<string>;
  disabled?: boolean;
  className?: string;
}

export function ProductImageUpload({
  value,
  previewUrl,
  name,
  onChange,
  onPreviewChange,
  onUpload,
  disabled,
  className,
}: ProductImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);

  // Prefer local blob preview while uploading / right after pick; else saved media URL.
  const displaySrc =
    previewUrl ||
    resolveProductImageUrl(value) ||
    undefined;

  useEffect(() => {
    setImgFailed(false);
  }, [displaySrc]);

  // Drop blob preview once the saved media URL is available (and keep it if remote fails).
  useEffect(() => {
    if (!previewUrl?.startsWith("blob:")) return;
    const resolved = resolveProductImageUrl(value);
    if (!resolved) return;
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(previewUrl);
      onPreviewChange?.(null);
    };
    img.src = resolved;
  }, [value, previewUrl, onPreviewChange]);

  const processFile = useCallback(
    async (file: File) => {
      setError(null);
      setImgFailed(false);
      if (!file.type.startsWith("image/")) {
        setError("Please select an image file (JPEG, PNG, WebP, or GIF).");
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`Image must be ${MAX_MB} MB or smaller.`);
        return;
      }

      const localPreview = URL.createObjectURL(file);
      onPreviewChange?.(localPreview);
      setUploading(true);
      try {
        const url = await onUpload(file);
        onChange(url);
        // Keep blob preview until the saved URL is in `value` and can display.
        // Parent clears previewUrl after form.image updates; only revoke then.
      } catch (err) {
        URL.revokeObjectURL(localPreview);
        onPreviewChange?.(null);
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onChange, onPreviewChange, onUpload]
  );

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) processFile(file);
  };

  const clearImage = () => {
    if (previewUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrl);
    }
    onChange("");
    onPreviewChange?.(null);
    setError(null);
    setImgFailed(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className={cn("space-y-4", className)}>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        disabled={disabled || uploading}
        onChange={(e) => handleFiles(e.target.files)}
      />

      {displaySrc && !imgFailed ? (
        <div className="relative max-w-sm overflow-hidden rounded-2xl border border-border/60 bg-muted/20">
          <img
            key={displaySrc}
            src={displaySrc}
            alt={name || "Product"}
            onError={() => setImgFailed(true)}
            className="aspect-[4/3] w-full object-cover"
          />
          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}
          {!uploading && (
            <div className="absolute top-2 right-2 flex gap-1">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-8 shadow-sm"
                disabled={disabled}
                onClick={() => inputRef.current?.click()}
              >
                Replace
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-8 w-8 p-0 shadow-sm"
                disabled={disabled}
                onClick={clearImage}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      ) : (
        <button
          type="button"
          disabled={disabled || uploading}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={cn(
            "flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 transition-all",
            dragOver
              ? "border-primary bg-primary/5 shadow-[0_0_0_4px_hsl(var(--primary)/0.08)]"
              : "border-border/60 bg-muted/15 hover:border-primary/35 hover:bg-muted/30",
            (disabled || uploading) && "pointer-events-none opacity-60"
          )}
        >
          {uploading ? (
            <Loader2 className="mb-3 h-10 w-10 animate-spin text-primary" />
          ) : (
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-[inset_0_1px_0_hsl(var(--background)/0.5)]">
              <Upload className="h-7 w-7" />
            </div>
          )}
          <p className="text-sm font-semibold tracking-tight text-foreground">
            {uploading ? "Uploading image..." : "Drop image here or click to browse"}
          </p>
          <p className="mt-1.5 text-center text-xs text-muted-foreground">
            JPEG, PNG, WebP or GIF · Max {MAX_MB} MB
          </p>
        </button>
      )}

      {error && (
        <p className="max-w-md rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}

      {!displaySrc && (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImageIcon className="h-3.5 w-3.5" />
          Product photo appears in catalog, POS, and receipts.
        </p>
      )}
    </div>
  );
}
