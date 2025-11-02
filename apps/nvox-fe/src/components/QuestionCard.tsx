import { useState, useEffect } from 'react';
import { Question } from '../types/api';

interface QuestionCardProps {
  question: Question;
  onSubmit: (questionId: string, value: number | boolean | string) => Promise<void>;
  disabled?: boolean;
  isViewingPrevious?: boolean;
}

export function QuestionCard({ question, onSubmit, disabled, isViewingPrevious = false }: QuestionCardProps) {
  const [value, setValue] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Check if this question has been answered (for display purposes only, still allow editing)
  const hasAnswer = question.previous_answer !== undefined;

  // Check if this is a yes/no question (string type with yes/no in text)
  const isYesNoQuestion = (question.type === 'text' || question.type === 'string' || (question.type !== 'number' && question.type !== 'boolean')) &&
    question.text.toLowerCase().includes('(yes/no)');

  // Sync value when question changes
  useEffect(() => {
    setValue(question.previous_answer !== undefined ? String(question.previous_answer) : '');
  }, [question.id, question.previous_answer]);

  const handleNumberOrTextSubmit = async () => {
    setError('');
    setLoading(true);

    try {
      let parsedValue: number | string;

      if (question.type === 'number') {
        parsedValue = parseFloat(value);
        if (isNaN(parsedValue)) {
          setError('Please enter a valid number');
          setLoading(false);
          return;
        }

        // Check constraints
        if (question.constraints) {
          if (question.constraints.min !== undefined && parsedValue < question.constraints.min) {
            setError(`Value must be at least ${question.constraints.min}`);
            setLoading(false);
            return;
          }
          if (question.constraints.max !== undefined && parsedValue > question.constraints.max) {
            setError(`Value must be at most ${question.constraints.max}`);
            setLoading(false);
            return;
          }
        }
      } else {
        parsedValue = value;
      }

      await onSubmit(question.id, parsedValue);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleBooleanSubmit = async (boolValue: boolean) => {
    if (loading) return;

    setError('');
    setLoading(true);

    try {
      await onSubmit(question.id, boolValue);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleYesNoSubmit = async (answer: string) => {
    if (loading) return;

    // Immediately set the value for visual feedback
    setValue(answer);
    setError('');
    setLoading(true);

    try {
      await onSubmit(question.id, answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Reset value on error
      setValue('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{question.text}</h3>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      {question.type === 'number' && (
        <div className="space-y-4">
          <input
            type="number"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="input"
            placeholder={`Enter value${question.constraints ? ` (${question.constraints.min}-${question.constraints.max})` : ''}`}
            min={question.constraints?.min}
            max={question.constraints?.max}
            disabled={disabled || loading || isViewingPrevious}
          />
          {question.constraints && (
            <p className="text-sm text-gray-500">
              Range: {question.constraints.min} - {question.constraints.max}
            </p>
          )}
        </div>
      )}

      {question.type === 'boolean' && (
        <div>
          <div className="flex space-x-4 mb-2">
            <button
              type="button"
              onClick={() => handleBooleanSubmit(true)}
              className={`flex-1 py-4 rounded-lg border-2 transition-colors font-semibold ${
                value === 'true' && hasAnswer
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'hover:border-primary-400 hover:bg-primary-50 border-gray-300 bg-white text-gray-900'
              }`}
              disabled={disabled || loading || isViewingPrevious}
            >
              {loading ? 'Submitting...' : value === 'true' && hasAnswer ? 'Yes ✓' : 'Yes'}
            </button>
            <button
              type="button"
              onClick={() => handleBooleanSubmit(false)}
              className={`flex-1 py-4 rounded-lg border-2 transition-colors font-semibold ${
                value === 'false' && hasAnswer
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'hover:border-primary-400 hover:bg-primary-50 border-gray-300 bg-white text-gray-900'
              }`}
              disabled={disabled || loading || isViewingPrevious}
            >
              {loading ? 'Submitting...' : value === 'false' && hasAnswer ? 'No ✓' : 'No'}
            </button>
          </div>
          <p className="text-sm text-gray-500 text-center">
            {isViewingPrevious ? 'Read-only view' : hasAnswer ? 'Click to change your answer' : 'Click Yes or No to submit your answer'}
          </p>
        </div>
      )}

      {isYesNoQuestion && (
        <div>
          <div className="flex space-x-4 mb-2">
            <button
              type="button"
              onClick={() => handleYesNoSubmit('yes')}
              className={`flex-1 py-4 rounded-lg border-2 transition-colors font-semibold ${
                value === 'yes'
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'hover:border-primary-400 hover:bg-primary-50 border-gray-300 bg-white text-gray-900'
              }`}
              disabled={disabled || loading || isViewingPrevious}
            >
              {loading && value === 'yes' ? 'Submitting...' : value === 'yes' ? 'Yes ✓' : 'Yes'}
            </button>
            <button
              type="button"
              onClick={() => handleYesNoSubmit('no')}
              className={`flex-1 py-4 rounded-lg border-2 transition-colors font-semibold ${
                value === 'no'
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'hover:border-primary-400 hover:bg-primary-50 border-gray-300 bg-white text-gray-900'
              }`}
              disabled={disabled || loading || isViewingPrevious}
            >
              {loading && value === 'no' ? 'Submitting...' : value === 'no' ? 'No ✓' : 'No'}
            </button>
          </div>
          <p className="text-sm text-gray-500 text-center">
            {isViewingPrevious ? 'Read-only view' : hasAnswer ? 'Click to change your answer' : 'Click Yes or No to submit your answer'}
          </p>
        </div>
      )}

      {(question.type === 'text' || question.type === 'string') && !isYesNoQuestion && (
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="input"
          placeholder="Enter your answer"
          disabled={disabled || loading || isViewingPrevious}
        />
      )}

      {question.type !== 'boolean' && !isYesNoQuestion && (
        <button
          onClick={handleNumberOrTextSubmit}
          disabled={!value || disabled || loading || isViewingPrevious}
          className={`w-full mt-4 ${isViewingPrevious ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'btn-primary'}`}
        >
          {isViewingPrevious ? 'Read-only' : loading ? 'Submitting...' : hasAnswer ? 'Update Answer' : 'Submit Answer'}
        </button>
      )}
    </div>
  );
}
