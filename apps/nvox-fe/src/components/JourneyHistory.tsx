import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import { StageHistoryItem, StageDetailsResponse } from '../types/api';
import { QuestionCard } from './QuestionCard';

interface JourneyHistoryProps {
  onClose: () => void;
}

export function JourneyHistory({ onClose }: JourneyHistoryProps) {
  const [stages, setStages] = useState<StageHistoryItem[]>([]);
  const [selectedStage, setSelectedStage] = useState<StageDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setError('');
      setLoading(true);
      const data = await apiClient.getJourneyHistory();
      setStages(data.stages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const loadStageDetails = async (stageId: string) => {
    try {
      setError('');
      setLoading(true);
      const data = await apiClient.getStageDetails(stageId);
      setSelectedStage(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stage details');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToList = () => {
    setSelectedStage(null);
  };

  if (loading && stages.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading history...</p>
        </div>
      </div>
    );
  }

  if (error && stages.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="card max-w-md">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error</h2>
          <p className="text-gray-700 mb-4">{error}</p>
          <button onClick={loadHistory} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {selectedStage ? 'Stage Details' : 'Journey History'}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {selectedStage
                ? `View your answers for ${selectedStage.stage_name}`
                : 'View all stages you have completed'}
            </p>
          </div>
          <button onClick={onClose} className="btn-secondary">
            Back to Journey
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {selectedStage ? (
          /* Stage Details View */
          <div>
            <button
              onClick={handleBackToList}
              className="mb-6 text-primary-600 hover:text-primary-700 flex items-center"
            >
              <svg
                className="w-5 h-5 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              Back to History
            </button>

            <div className="card mb-6">
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                {selectedStage.stage_name}
              </h2>
              <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                <div>
                  <span className="font-semibold">Entered:</span>{' '}
                  {new Date(selectedStage.entered_at).toLocaleString()}
                </div>
                {selectedStage.exited_at && (
                  <div>
                    <span className="font-semibold">Exited:</span>{' '}
                    {new Date(selectedStage.exited_at).toLocaleString()}
                  </div>
                )}
                <div>
                  <span className="font-semibold">Visit:</span> #{selectedStage.visit_number}
                </div>
                {selectedStage.is_current && (
                  <div className="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
                    Current Stage
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <h3 className="text-lg font-bold text-gray-900">
                Questions & Answers ({selectedStage.questions.length})
              </h3>
              {selectedStage.questions.map((question) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  onSubmit={async () => {}}
                  disabled={true}
                />
              ))}
            </div>
          </div>
        ) : (
          /* Stage List View */
          <div>
            {stages.length === 0 ? (
              <div className="card text-center">
                <p className="text-gray-600">No stages visited yet.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {stages.map((stage, index) => (
                  <button
                    key={`${stage.stage_id}-${stage.visit_number}`}
                    onClick={() => loadStageDetails(stage.stage_id)}
                    className="w-full card hover:shadow-lg transition-shadow text-left"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 text-primary-700 font-bold text-sm">
                            {index + 1}
                          </div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            {stage.stage_name}
                          </h3>
                          {stage.is_current && (
                            <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">
                              Current
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-4 text-sm text-gray-600 ml-11">
                          <div>
                            <span className="font-semibold">Entered:</span>{' '}
                            {new Date(stage.entered_at).toLocaleDateString()}
                          </div>
                          {stage.exited_at && (
                            <div>
                              <span className="font-semibold">Exited:</span>{' '}
                              {new Date(stage.exited_at).toLocaleDateString()}
                            </div>
                          )}
                          <div>
                            <span className="font-semibold">Questions Answered:</span>{' '}
                            {stage.questions_answered}
                          </div>
                          <div>
                            <span className="font-semibold">Visit:</span> #{stage.visit_number}
                          </div>
                        </div>
                      </div>
                      <svg
                        className="w-6 h-6 text-gray-400 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
