import { useState, useEffect, useCallback } from 'react';
import { Answer, AnswerListItem, ClueInfo } from '../../types';
import {
  getAnswers,
  getAnswer,
  createAnswer,
  deleteAnswer,
  createClue,
  updateClue,
  deleteClue,
  importAnswers,
} from '../../api/answers';
import './ClueDatabase.css';

interface ClueDatabaseProps {
  onSelectAnswer?: (answer: Answer) => void;
}

export function ClueDatabase({ onSelectAnswer }: ClueDatabaseProps) {
  const [answers, setAnswers] = useState<AnswerListItem[]>([]);
  const [selectedAnswer, setSelectedAnswer] = useState<Answer | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Search/filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [minLength, setMinLength] = useState<number | ''>('');
  const [maxLength, setMaxLength] = useState<number | ''>('');
  const [tagFilter, setTagFilter] = useState('');

  // New answer form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newWord, setNewWord] = useState('');
  const [newClueText, setNewClueText] = useState('');
  const [newDifficulty, setNewDifficulty] = useState(3);
  const [newTags, setNewTags] = useState('');

  // Edit clue state
  const [editingClue, setEditingClue] = useState<ClueInfo | null>(null);
  const [editClueText, setEditClueText] = useState('');
  const [editDifficulty, setEditDifficulty] = useState(3);
  const [editTags, setEditTags] = useState('');

  // Add clue to existing answer
  const [addingClueToAnswer, setAddingClueToAnswer] = useState(false);
  const [addClueText, setAddClueText] = useState('');
  const [addDifficulty, setAddDifficulty] = useState(3);
  const [addTags, setAddTags] = useState('');

  // Import state
  const [showImport, setShowImport] = useState(false);

  const showMessage = useCallback((type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  }, []);

  const loadAnswers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getAnswers({
        q: searchQuery || undefined,
        min_length: minLength || undefined,
        max_length: maxLength || undefined,
        tag: tagFilter || undefined,
        limit: 100,
      });
      setAnswers(data);
    } catch {
      showMessage('error', 'Failed to load answers');
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, minLength, maxLength, tagFilter, showMessage]);

  useEffect(() => {
    loadAnswers();
  }, [loadAnswers]);

  const handleSelectAnswer = async (id: number) => {
    try {
      const answer = await getAnswer(id);
      setSelectedAnswer(answer);
      onSelectAnswer?.(answer);
    } catch {
      showMessage('error', 'Failed to load answer details');
    }
  };

  const handleCreateAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWord.trim()) return;

    try {
      const clues = newClueText.trim()
        ? [{ clue_text: newClueText, difficulty: newDifficulty, tags: newTags || undefined }]
        : undefined;

      await createAnswer({ word: newWord, clues });
      showMessage('success', `Added "${newWord.toUpperCase()}"`);
      setNewWord('');
      setNewClueText('');
      setNewDifficulty(3);
      setNewTags('');
      setShowAddForm(false);
      loadAnswers();
    } catch (err) {
      showMessage('error', err instanceof Error ? err.message : 'Failed to create answer');
    }
  };

  const handleDeleteAnswer = async (id: number) => {
    if (!confirm('Delete this answer and all its clues?')) return;

    try {
      await deleteAnswer(id);
      showMessage('success', 'Answer deleted');
      if (selectedAnswer?.id === id) {
        setSelectedAnswer(null);
      }
      loadAnswers();
    } catch {
      showMessage('error', 'Failed to delete answer');
    }
  };

  const handleAddClue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAnswer || !addClueText.trim()) return;

    try {
      await createClue(selectedAnswer.id, {
        clue_text: addClueText,
        difficulty: addDifficulty,
        tags: addTags || undefined,
      });
      showMessage('success', 'Clue added');
      setAddClueText('');
      setAddDifficulty(3);
      setAddTags('');
      setAddingClueToAnswer(false);
      const updated = await getAnswer(selectedAnswer.id);
      setSelectedAnswer(updated);
      loadAnswers();
    } catch {
      showMessage('error', 'Failed to add clue');
    }
  };

  const handleStartEditClue = (clue: ClueInfo) => {
    setEditingClue(clue);
    setEditClueText(clue.clue_text);
    setEditDifficulty(clue.difficulty);
    setEditTags(clue.tags || '');
  };

  const handleSaveClue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAnswer || !editingClue) return;

    try {
      await updateClue(selectedAnswer.id, editingClue.id, {
        clue_text: editClueText,
        difficulty: editDifficulty,
        tags: editTags || undefined,
      });
      showMessage('success', 'Clue updated');
      setEditingClue(null);
      const updated = await getAnswer(selectedAnswer.id);
      setSelectedAnswer(updated);
    } catch {
      showMessage('error', 'Failed to update clue');
    }
  };

  const handleDeleteClue = async (clueId: number) => {
    if (!selectedAnswer || !confirm('Delete this clue?')) return;

    try {
      await deleteClue(selectedAnswer.id, clueId);
      showMessage('success', 'Clue deleted');
      const updated = await getAnswer(selectedAnswer.id);
      setSelectedAnswer(updated);
      loadAnswers();
    } catch {
      showMessage('error', 'Failed to delete clue');
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await importAnswers(file);
      showMessage(
        'success',
        `Imported ${result.imported} entries, skipped ${result.skipped}${
          result.errors.length > 0 ? `. Errors: ${result.errors.slice(0, 3).join('; ')}` : ''
        }`
      );
      loadAnswers();
      setShowImport(false);
    } catch (err) {
      showMessage('error', err instanceof Error ? err.message : 'Import failed');
    }

    e.target.value = '';
  };

  const renderDifficultyStars = (difficulty: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={`star ${i < difficulty ? 'filled' : ''}`}>
        {i < difficulty ? '\u2605' : '\u2606'}
      </span>
    ));
  };

  return (
    <div className="clue-database">
      {message && (
        <div className={`message message-${message.type}`}>{message.text}</div>
      )}

      <div className="clue-database-header">
        <h2>Clue Database</h2>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => setShowAddForm(true)}>
            Add Word
          </button>
          <button className="btn btn-secondary" onClick={() => setShowImport(true)}>
            Import CSV
          </button>
        </div>
      </div>

      <div className="clue-database-content">
        <div className="answers-panel">
          <div className="search-filters">
            <input
              type="text"
              placeholder="Search words..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <div className="filter-row">
              <input
                type="number"
                placeholder="Min"
                value={minLength}
                onChange={(e) => setMinLength(e.target.value ? parseInt(e.target.value) : '')}
                className="length-input"
                min={1}
                max={21}
              />
              <span className="filter-separator">-</span>
              <input
                type="number"
                placeholder="Max"
                value={maxLength}
                onChange={(e) => setMaxLength(e.target.value ? parseInt(e.target.value) : '')}
                className="length-input"
                min={1}
                max={21}
              />
              <input
                type="text"
                placeholder="Tag filter"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                className="tag-input"
              />
            </div>
          </div>

          <div className="answers-list">
            {isLoading ? (
              <div className="loading">Loading...</div>
            ) : answers.length === 0 ? (
              <div className="empty-state">
                No answers found. Add some words to get started!
              </div>
            ) : (
              answers.map((answer) => (
                <div
                  key={answer.id}
                  className={`answer-item ${selectedAnswer?.id === answer.id ? 'selected' : ''}`}
                  onClick={() => handleSelectAnswer(answer.id)}
                >
                  <div className="answer-word">{answer.word}</div>
                  <div className="answer-meta">
                    <span className="answer-length">{answer.length} letters</span>
                    <span className="answer-clues">{answer.clue_count} clue{answer.clue_count !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="detail-panel">
          {selectedAnswer ? (
            <>
              <div className="detail-header">
                <h3>{selectedAnswer.word}</h3>
                <div className="detail-actions">
                  <button
                    className="btn btn-small btn-primary"
                    onClick={() => setAddingClueToAnswer(true)}
                  >
                    Add Clue
                  </button>
                  <button
                    className="btn btn-small btn-danger"
                    onClick={() => handleDeleteAnswer(selectedAnswer.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="clues-list">
                <h4>Clues ({selectedAnswer.clues.length})</h4>
                {selectedAnswer.clues.length === 0 ? (
                  <div className="empty-clues">No clues yet. Add one!</div>
                ) : (
                  selectedAnswer.clues.map((clue) => (
                    <div key={clue.id} className="clue-item">
                      {editingClue?.id === clue.id ? (
                        <form onSubmit={handleSaveClue} className="edit-clue-form">
                          <textarea
                            value={editClueText}
                            onChange={(e) => setEditClueText(e.target.value)}
                            placeholder="Clue text"
                            required
                          />
                          <div className="form-row">
                            <label>
                              Difficulty:
                              <select
                                value={editDifficulty}
                                onChange={(e) => setEditDifficulty(parseInt(e.target.value))}
                              >
                                {[1, 2, 3, 4, 5].map((d) => (
                                  <option key={d} value={d}>
                                    {d} - {['Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard'][d - 1]}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <input
                              type="text"
                              value={editTags}
                              onChange={(e) => setEditTags(e.target.value)}
                              placeholder="Tags (comma-separated)"
                            />
                          </div>
                          <div className="form-actions">
                            <button type="submit" className="btn btn-small btn-primary">
                              Save
                            </button>
                            <button
                              type="button"
                              className="btn btn-small btn-secondary"
                              onClick={() => setEditingClue(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        </form>
                      ) : (
                        <>
                          <div className="clue-text">{clue.clue_text}</div>
                          <div className="clue-meta">
                            <span className="clue-difficulty">
                              {renderDifficultyStars(clue.difficulty)}
                            </span>
                            {clue.tags && (
                              <span className="clue-tags">
                                {clue.tags.split(',').map((tag, i) => (
                                  <span key={i} className="tag">
                                    {tag.trim()}
                                  </span>
                                ))}
                              </span>
                            )}
                          </div>
                          <div className="clue-actions">
                            <button
                              className="btn btn-small btn-secondary"
                              onClick={() => handleStartEditClue(clue)}
                            >
                              Edit
                            </button>
                            <button
                              className="btn btn-small btn-danger"
                              onClick={() => handleDeleteClue(clue.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  ))
                )}
              </div>

              {addingClueToAnswer && (
                <form onSubmit={handleAddClue} className="add-clue-form">
                  <h4>Add New Clue</h4>
                  <textarea
                    value={addClueText}
                    onChange={(e) => setAddClueText(e.target.value)}
                    placeholder="Enter clue text..."
                    required
                    autoFocus
                  />
                  <div className="form-row">
                    <label>
                      Difficulty:
                      <select
                        value={addDifficulty}
                        onChange={(e) => setAddDifficulty(parseInt(e.target.value))}
                      >
                        {[1, 2, 3, 4, 5].map((d) => (
                          <option key={d} value={d}>
                            {d} - {['Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard'][d - 1]}
                          </option>
                        ))}
                      </select>
                    </label>
                    <input
                      type="text"
                      value={addTags}
                      onChange={(e) => setAddTags(e.target.value)}
                      placeholder="Tags (comma-separated)"
                    />
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary">
                      Add Clue
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setAddingClueToAnswer(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </>
          ) : (
            <div className="no-selection">
              Select an answer to view and edit its clues
            </div>
          )}
        </div>
      </div>

      {/* Add Answer Modal */}
      {showAddForm && (
        <div className="modal-overlay" onClick={() => setShowAddForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add New Word</h3>
            <form onSubmit={handleCreateAnswer}>
              <div className="form-group">
                <label>Word</label>
                <input
                  type="text"
                  value={newWord}
                  onChange={(e) => setNewWord(e.target.value.toUpperCase())}
                  placeholder="Enter word (e.g., PIANO)"
                  required
                  autoFocus
                  pattern="[A-Za-z]+"
                />
              </div>
              <div className="form-group">
                <label>Clue (optional)</label>
                <textarea
                  value={newClueText}
                  onChange={(e) => setNewClueText(e.target.value)}
                  placeholder="Enter a clue for this word..."
                />
              </div>
              {newClueText && (
                <>
                  <div className="form-group">
                    <label>Difficulty</label>
                    <select
                      value={newDifficulty}
                      onChange={(e) => setNewDifficulty(parseInt(e.target.value))}
                    >
                      {[1, 2, 3, 4, 5].map((d) => (
                        <option key={d} value={d}>
                          {d} - {['Very Easy', 'Easy', 'Medium', 'Hard', 'Very Hard'][d - 1]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Tags</label>
                    <input
                      type="text"
                      value={newTags}
                      onChange={(e) => setNewTags(e.target.value)}
                      placeholder="music, instruments (comma-separated)"
                    />
                  </div>
                </>
              )}
              <div className="modal-actions">
                <button type="submit" className="btn btn-primary">
                  Add Word
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImport && (
        <div className="modal-overlay" onClick={() => setShowImport(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Import Words & Clues</h3>
            <p className="import-help">
              Upload a CSV file with the following format:
              <br />
              <code>word,clue,difficulty,tags</code>
              <br />
              <br />
              Example:
              <br />
              <code>PIANO,"Baby grand, for one",3,music</code>
            </p>
            <div className="import-actions">
              <input
                type="file"
                accept=".csv,.txt"
                onChange={handleImport}
                id="import-file"
                className="file-input"
              />
              <label htmlFor="import-file" className="btn btn-primary">
                Choose File
              </label>
              <button
                className="btn btn-secondary"
                onClick={() => setShowImport(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
