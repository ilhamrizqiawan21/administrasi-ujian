import { Eye, Pencil, Trash2 } from "lucide-react";
import { IconButton } from "../ui/Button";

export interface RowActionsProps {
  itemLabel: string;
  onView?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  deleteDisabled?: boolean;
}

export function RowActions({
  itemLabel,
  onView,
  onEdit,
  onDelete,
  deleteDisabled = false,
}: RowActionsProps) {
  return (
    <div className="uc-actions" style={{ justifyContent: "flex-end" }}>
      {onView && (
        <IconButton
          label={`Lihat ${itemLabel}`}
          icon={<Eye size={16} aria-hidden="true" />}
          onClick={onView}
        />
      )}
      {onEdit && (
        <IconButton
          label={`Edit ${itemLabel}`}
          icon={<Pencil size={16} aria-hidden="true" />}
          onClick={onEdit}
        />
      )}
      {onDelete && (
        <IconButton
          label={`Hapus ${itemLabel}`}
          icon={<Trash2 size={16} aria-hidden="true" />}
          variant="destructive"
          disabled={deleteDisabled}
          onClick={onDelete}
        />
      )}
    </div>
  );
}
