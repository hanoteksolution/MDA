import { useCallback, useRef, useState } from "react";
import { Upload, X, Loader2, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";
import { ProductImagePreview } from "@/components/catalog/ProductImage";

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
  sku,
  categoryName,
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

  const displayImage = previewUrl || value;

  const processFile = useCallback(
    async (file: File) => {
      setError(null);
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
      } catch (err) {
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
    onChange("");
    onPreviewChange?.(null);
    setError(null);
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

      {displayImage ? (
        <div className="relative max-w-xs">
          <ProductImagePreview
            image={displayImage}
            name={name}
            sku={sku}
            categoryName={categoryName}
          />
          {uploading && (
            <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-background/80">
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
            "flex w-full max-w-md flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 transition-colors",
            dragOver ? "border-primary bg-primary/5" : "border-border bg-muted/20 hover:border-primary/40 hover:bg-muted/40",
            (disabled || uploading) && "pointer-events-none opacity-60"
          )}
        >
          {uploading ? (
            <Loader2 className="h-10 w-10 animate-spin text-primary mb-3" />
          ) : (
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
              <Upload className="h-6 w-6" />
            </div>
          )}
          <p className="text-sm font-semibold text-foreground">
            {uploading ? "Uploading..." : "Click or drag image to upload"}
          </p>
          <p className="text-xs text-muted-foreground mt-1 text-center">
            JPEG, PNG, WebP or GIF · Max {MAX_MB} MB
          </p>
        </button>
      )}

      {error && (
        <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2 max-w-md">{error}</p>
      )}

      {!displayImage && (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImageIcon className="h-3.5 w-3.5" />
          Product photo appears in catalog, POS, and receipts.
        </p>
      )}
    </div>
  );
}
