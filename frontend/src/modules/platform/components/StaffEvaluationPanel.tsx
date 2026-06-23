import { useState } from "react";
import { Save, Star, X } from "lucide-react";
import { ContentSection } from "@/components/layout/ContentSection";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/button";
import { staffPerformanceApi, type StaffPerformanceRow } from "@/services/api/platform";
import { cn } from "@/utils/cn";

interface StaffEvaluationPanelProps {
  staff: StaffPerformanceRow;
  period: string;
  onSaved: (staffId: string, rating: number, notes: string) => void;
  onClose: () => void;
}

function StarRating({
  value,
  onChange,
}: {
  value: number;
  onChange: (rating: number) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          className={cn(
            "rounded p-1 transition-colors hover:bg-muted",
            star <= value ? "text-amber-500" : "text-muted-foreground/40"
          )}
          aria-label={`Rate ${star} out of 5`}
        >
          <Star className={cn("h-6 w-6", star <= value && "fill-current")} />
        </button>
      ))}
      <span className="ml-2 text-sm text-muted-foreground">{value}/5</span>
    </div>
  );
}

export function StaffEvaluationPanel({ staff, period, onSaved, onClose }: StaffEvaluationPanelProps) {
  const [rating, setRating] = useState(staff.evaluation?.rating ?? 3);
  const [notes, setNotes] = useState(staff.evaluation?.notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await staffPerformanceApi.saveEvaluation(staff.user_id, { period, rating, notes });
      onSaved(staff.user_id, rating, notes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save evaluation.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ContentSection
      title={`Evaluate — ${staff.full_name}`}
      description={`${staff.role} · ${staff.branch}`}
      action={
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
          Close
        </Button>
      }
    >
      <form onSubmit={save} className="space-y-4">
        <FormField label="Manager rating">
          <StarRating value={rating} onChange={setRating} />
        </FormField>

        <FormField
          label="Manager notes"
          hint="Attendance, customer service, teamwork, punctuality, or goals for next period."
        >
          <textarea
            className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Strong sales this week. Needs improvement on stock counts."
          />
        </FormField>

        {staff.evaluation && (
          <p className="text-xs text-muted-foreground">
            Last updated by {staff.evaluation.evaluator_name} on{" "}
            {new Date(staff.evaluation.updated_at).toLocaleString()}
          </p>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            <Save className="h-4 w-4" />
            Save Evaluation
          </Button>
        </div>
      </form>
    </ContentSection>
  );
}

export function RatingBadge({ rating }: { rating?: number | null }) {
  if (!rating) {
    return <span className="text-xs text-muted-foreground">Not rated</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-600">
      <Star className="h-3.5 w-3.5 fill-amber-500 text-amber-500" />
      {rating}/5
    </span>
  );
}
