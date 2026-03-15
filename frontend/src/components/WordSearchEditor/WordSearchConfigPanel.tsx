import { WordSearchConfig, WordSearchDirection } from '../../types';

const ALL_DIRECTIONS: { value: WordSearchDirection; label: string }[] = [
  { value: 'E',  label: '→ East (left to right)' },
  { value: 'W',  label: '← West (right to left)' },
  { value: 'S',  label: '↓ South (top to bottom)' },
  { value: 'N',  label: '↑ North (bottom to top)' },
  { value: 'SE', label: '↘ Southeast (diagonal)' },
  { value: 'SW', label: '↙ Southwest (diagonal)' },
  { value: 'NE', label: '↗ Northeast (diagonal)' },
  { value: 'NW', label: '↖ Northwest (diagonal)' },
];

const SIZE_PRESETS = [
  { label: '10×10', rows: 10, cols: 10 },
  { label: '15×15', rows: 15, cols: 15 },
  { label: '20×20', rows: 20, cols: 20 },
  { label: 'Custom', rows: 0, cols: 0 },
];

interface WordSearchConfigPanelProps {
  config: WordSearchConfig;
  onChange: (config: WordSearchConfig) => void;
  onGenerate: () => void;
  isGenerating: boolean;
  unplacedCount: number;
}

export function WordSearchConfigPanel({
  config,
  onChange,
  onGenerate,
  isGenerating,
  unplacedCount,
}: WordSearchConfigPanelProps) {
  const isPreset = SIZE_PRESETS.some(p => p.rows === config.rows && p.cols === config.cols && p.rows !== 0);
  const selectedPreset = isPreset
    ? `${config.rows}×${config.cols}`
    : 'Custom';

  const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const preset = SIZE_PRESETS.find(p => p.label === e.target.value);
    if (preset && preset.rows !== 0) {
      onChange({ ...config, rows: preset.rows, cols: preset.cols });
    }
  };

  const handleDirectionToggle = (dir: WordSearchDirection) => {
    const has = config.allowedDirections.includes(dir);
    if (has && config.allowedDirections.length === 1) return; // keep at least one
    const next = has
      ? config.allowedDirections.filter(d => d !== dir)
      : [...config.allowedDirections, dir];
    onChange({ ...config, allowedDirections: next });
  };

  return (
    <div className="ws-config-panel">
      <h3>Configuration</h3>

      <div className="ws-config-section">
        <label className="ws-label">Grid Size</label>
        <select
          className="ws-select"
          value={selectedPreset}
          onChange={handlePresetChange}
        >
          {SIZE_PRESETS.filter(p => p.rows !== 0).map(p => (
            <option key={p.label} value={p.label}>{p.label}</option>
          ))}
          <option value="Custom">Custom</option>
        </select>

        {!isPreset && (
          <div className="ws-custom-size">
            <label>
              Rows:
              <input
                type="number"
                min={5}
                max={50}
                value={config.rows}
                onChange={e => onChange({ ...config, rows: Math.max(5, Math.min(50, +e.target.value || 10)) })}
                className="ws-number-input"
              />
            </label>
            <label>
              Cols:
              <input
                type="number"
                min={5}
                max={50}
                value={config.cols}
                onChange={e => onChange({ ...config, cols: Math.max(5, Math.min(50, +e.target.value || 10)) })}
                className="ws-number-input"
              />
            </label>
          </div>
        )}
      </div>

      <div className="ws-config-section">
        <label className="ws-label">Word Directions</label>
        <div className="ws-directions">
          {ALL_DIRECTIONS.map(({ value, label }) => (
            <label key={value} className="ws-direction-label">
              <input
                type="checkbox"
                checked={config.allowedDirections.includes(value)}
                onChange={() => handleDirectionToggle(value)}
              />
              {label}
            </label>
          ))}
        </div>
        <button
          className="ws-link-btn"
          onClick={() => onChange({ ...config, allowedDirections: ALL_DIRECTIONS.map(d => d.value) })}
        >
          Select all
        </button>
        {' · '}
        <button
          className="ws-link-btn"
          onClick={() => onChange({ ...config, allowedDirections: ['E', 'S'] })}
        >
          Easy (→↓ only)
        </button>
      </div>

      <button
        className="btn btn-primary ws-generate-btn"
        onClick={onGenerate}
        disabled={isGenerating}
      >
        {isGenerating ? 'Generating...' : 'Generate Puzzle'}
      </button>

      {unplacedCount > 0 && (
        <p className="ws-unplaced-warning">
          {unplacedCount} word{unplacedCount > 1 ? 's' : ''} couldn't fit — try a larger grid or fewer words.
        </p>
      )}
    </div>
  );
}
