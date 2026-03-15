import { WordSearchPlacement } from '../../types';
import { getPlacementCells } from '../../utils/wordSearchGenerator';

interface WordSearchGridProps {
  grid: string[][];
  placements: WordSearchPlacement[];
  selectedWord: string | null;
  highlightMode: boolean;
}

export function WordSearchGrid({ grid, placements, selectedWord, highlightMode }: WordSearchGridProps) {
  // Build a Set of "row,col" keys for the selected word's cells
  const highlightedCells = new Set<string>();
  if (highlightMode && selectedWord) {
    const placement = placements.find(p => p.word === selectedWord);
    if (placement) {
      for (const { row, col } of getPlacementCells(placement)) {
        highlightedCells.add(`${row},${col}`);
      }
    }
  }

  if (grid.length === 0) {
    return (
      <div className="ws-grid-empty">
        <p>Configure your word list and click Generate to create a puzzle.</p>
      </div>
    );
  }

  return (
    <div className="ws-grid-wrapper">
      <div
        className="ws-grid"
        style={{ gridTemplateColumns: `repeat(${grid[0]?.length ?? 1}, 1fr)` }}
      >
        {grid.map((row, r) =>
          row.map((letter, c) => {
            const key = `${r},${c}`;
            const isHighlighted = highlightedCells.has(key);
            return (
              <div
                key={key}
                className={`ws-cell${isHighlighted ? ' ws-cell-highlighted' : ''}`}
              >
                {letter}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
