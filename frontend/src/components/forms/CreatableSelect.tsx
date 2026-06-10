import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CREATE_VALUE = "__create_new__";
const NONE_VALUE = "__none__";

export interface CreatableOption {
  id: string;
  name: string;
}

interface CreatableSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CreatableOption[];
  placeholder?: string;
  disabled?: boolean;
  onCreate: (name: string) => Promise<CreatableOption>;
  createLabel?: string;
  className?: string;
  allowNone?: boolean;
}

export function CreatableSelect({
  value,
  onChange,
  options,
  placeholder = "Select...",
  disabled,
  onCreate,
  createLabel = "Create new...",
  className,
  allowNone,
}: CreatableSelectProps) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSelect = (v: string) => {
    if (v === CREATE_VALUE) {
      setCreating(true);
      setNewName("");
      return;
    }
    if (v === NONE_VALUE) {
      onChange("");
      return;
    }
    onChange(v);
  };

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setSaving(true);
    try {
      const created = await onCreate(name);
      onChange(created.id);
      setCreating(false);
      setNewName("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const selectValue = value || (allowNone ? NONE_VALUE : undefined);

  return (
    <div className={cn("space-y-2", className)}>
      <Select value={selectValue} onValueChange={handleSelect} disabled={disabled}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {allowNone && <SelectItem value={NONE_VALUE}>None</SelectItem>}
          {options.map((opt) => (
            <SelectItem key={opt.id} value={opt.id}>
              {opt.name}
            </SelectItem>
          ))}
          <SelectItem value={CREATE_VALUE} className="text-primary font-medium">
            <span className="flex items-center gap-2">
              <Plus className="h-3.5 w-3.5" />
              {createLabel}
            </span>
          </SelectItem>
        </SelectContent>
      </Select>

      {creating && (
        <div className="flex gap-2 rounded-xl border border-primary/30 bg-primary/5 p-3">
          <Input
            autoFocus
            placeholder="Enter name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleCreate())}
            className="h-9"
          />
          <Button type="button" size="sm" onClick={handleCreate} disabled={saving || !newName.trim()}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={() => setCreating(false)}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}
