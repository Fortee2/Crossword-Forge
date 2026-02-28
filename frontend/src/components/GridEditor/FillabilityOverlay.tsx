import { SlotFillability, FillabilitySummary, FillabilitySeverity } from '../../types';
import './FillabilityOverlay.css';

interface FillabilityOverlayProps {
  slots: SlotFillability[];
  summary: FillabilitySummary;
  gridSize: number;
}

export function FillabilityOverlay({ summary }: FillabilityOverlayProps) {
  const totalSlots = summary.good + summary.okay + summary.tight + summary.danger;

  return (
    <div className="fillability-overlay">
      <div className="fillability-summary">
        <span className="summary-item good">{summary.good} good</span>
        <span className="summary-item okay">{summary.okay} okay</span>
        <span className="summary-item tight">{summary.tight} tight</span>
        <span className="summary-item danger">{summary.danger} unfillable</span>
        <span className="summary-total">({totalSlots} slots)</span>
      </div>
    </div>
  );
}

// Utility function to get cell severity for grid rendering
export function getCellSeverity(
  slots: SlotFillability[],
  row: number,
  col: number
): FillabilitySeverity | null {
  const severityRank: Record<FillabilitySeverity, number> = {
    good: 0,
    okay: 1,
    tight: 2,
    danger: 3,
  };

  let worstSeverity: FillabilitySeverity | null = null;

  for (const slot of slots) {
    // Check if this cell is part of this slot
    let inSlot = false;
    if (slot.direction === 'across') {
      if (row === slot.row && col >= slot.col && col < slot.col + slot.length) {
        inSlot = true;
      }
    } else {
      if (col === slot.col && row >= slot.row && row < slot.row + slot.length) {
        inSlot = true;
      }
    }

    if (inSlot) {
      if (!worstSeverity || severityRank[slot.severity] > severityRank[worstSeverity]) {
        worstSeverity = slot.severity;
      }
    }
  }

  return worstSeverity;
}

// Get fill count badge for word list
interface FillCountBadgeProps {
  slots: SlotFillability[];
  number: number;
  direction: 'across' | 'down';
}

export function FillCountBadge({ slots, number, direction }: FillCountBadgeProps) {
  const slot = slots.find((s) => s.number === number && s.direction === direction);
  if (!slot) return null;

  const formatCount = (count: number): string => {
    if (count >= 10000) {
      return `${Math.floor(count / 1000)}k`;
    }
    return count.toString();
  };

  return (
    <span className={`fill-count-badge ${slot.severity}`} title={`${slot.fill_count} possible words`}>
      {formatCount(slot.fill_count)}
    </span>
  );
}
