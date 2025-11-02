import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import { JourneyState, StageHistoryItem, StageDetailsResponse } from '../types/api';
import { JourneyProgress } from './JourneyProgress';
import { QuestionCard } from './QuestionCard';
import { JourneyHistory } from './JourneyHistory';

interface JourneyViewProps {
  onLogout: () => void;
}

export function JourneyView({ onLogout }: JourneyViewProps) {
  const [journey, setJourney] = useState<JourneyState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [transitionMessage, setTransitionMessage] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [stageHistory, setStageHistory] = useState<StageHistoryItem[]>([]);
  const [viewingStageIndex, setViewingStageIndex] = useState<number | null>(null);
  const [viewingStageDetails, setViewingStageDetails] = useState<StageDetailsResponse | null>(null);

  const loadJourney = async () => {
    try {
      setError('');
      const data = await apiClient.getCurrentJourney();
      setJourney(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load journey');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJourney();
    loadStageHistory();
    const email = apiClient.getUserEmail();
    setUserEmail(email || 'User');
  }, []);

  const loadStageHistory = async () => {
    try {
      const history = await apiClient.getJourneyHistory();
      setStageHistory(history.stages);
    } catch (err) {
      console.error('Failed to load stage history:', err);
    }
  };

  const loadStageByIndex = async (index: number) => {
    if (index < 0 || index >= stageHistory.length) return;

    try {
      setLoading(true);
      setError('');
      const stage = stageHistory[index];
      const details = await apiClient.getStageDetails(stage.stage_id);
      setViewingStageDetails(details);
      setViewingStageIndex(index);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stage');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevious = () => {
    const currentIndex = viewingStageIndex !== null ? viewingStageIndex : stageHistory.length - 1;
    if (currentIndex > 0) {
      loadStageByIndex(currentIndex - 1);
    }
  };

  const handleNext = () => {
    const currentIndex = viewingStageIndex !== null ? viewingStageIndex : stageHistory.length - 1;
    const nextIndex = currentIndex + 1;

    // If next index is the last stage (current stage), go back to current journey view
    if (nextIndex === stageHistory.length - 1) {
      handleBackToCurrent();
    } else if (nextIndex < stageHistory.length - 1) {
      loadStageByIndex(nextIndex);
    }
  };

  const handleBackToCurrent = () => {
    setViewingStageIndex(null);
    setViewingStageDetails(null);
    loadJourney();
  };

  const handleAnswerSubmit = async (questionId: string, value: number | boolean | string) => {
    try {
      setTransitionMessage('');
      await apiClient.submitAnswer({
        question_id: questionId,
        answer_value: value,
      });

      // If viewing a previous stage, reload that stage's details
      // Otherwise reload the current journey
      if (isViewingPrevious && viewingStageIndex !== null) {
        await loadStageByIndex(viewingStageIndex);
      } else {
        await loadJourney();
      }
    } catch (err) {
      throw err; // Let QuestionCard handle the error
    }
  };

  const handleContinue = async () => {
    try {
      setError('');
      setLoading(true);
      const response = await apiClient.continueJourney();

      if (response.transition_occurred) {
        setTransitionMessage(
          `Stage transition: ${response.previous_stage} → ${response.current_stage}`
        );
      }

      // Reload journey to get new stage
      await loadJourney();
      // Reload stage history to include the new stage
      await loadStageHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to continue journey');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    onLogout();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your journey...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="card max-w-md">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error</h2>
          <p className="text-gray-700 mb-4">{error}</p>
          <button onClick={loadJourney} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!journey) {
    return null;
  }

  // Show history view if requested
  if (showHistory) {
    return <JourneyHistory onClose={() => setShowHistory(false)} />;
  }

  // Determine which stage data to display
  const isViewingPrevious = viewingStageDetails !== null;
  const currentIndex = viewingStageIndex !== null ? viewingStageIndex : stageHistory.length - 1;
  const canGoPrevious = currentIndex > 0;
  const canGoNext = currentIndex < stageHistory.length - 1;

  // Use viewing stage details if available, otherwise use current journey
  const displayStage = isViewingPrevious
    ? {
        stage_name: viewingStageDetails!.stage_name,
        questions: viewingStageDetails!.questions,
        stage_id: viewingStageDetails!.stage_id,
        visit_number: viewingStageDetails!.visit_number,
      }
    : {
        stage_name: journey.stage_name,
        questions: journey.questions,
        stage_id: journey.current_stage,
        visit_number: journey.visit_number,
      };

  // Check if all questions have been answered (only relevant for current stage)
  const allQuestionsAnswered = !isViewingPrevious && journey.questions.every(
    (q) => q.previous_answer !== undefined
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Transplant Journey</h1>
            <p className="text-sm text-gray-600 mt-1">Hello, {userEmail}</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setShowHistory(true)} className="btn-secondary">
              View History
            </button>
            <button onClick={handleLogout} className="btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Viewing Previous Stage Banner */}
        {isViewingPrevious && (
          <div className="mb-6 bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <svg
                  className="w-6 h-6 text-blue-500 mr-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-blue-800 font-medium">
                  Viewing previous stage (read-only)
                </p>
              </div>
              <button onClick={handleBackToCurrent} className="btn-primary">
                Back to Current Stage
              </button>
            </div>
          </div>
        )}

        {/* Stage Navigation */}
        {stageHistory.length > 1 && (
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={handlePrevious}
              disabled={!canGoPrevious}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-colors ${
                canGoPrevious
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Previous
            </button>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Stage {currentIndex + 1} of {stageHistory.length}
              </p>
              <p className="text-xs text-gray-500">
                {displayStage.stage_name}
              </p>
            </div>

            <button
              onClick={handleNext}
              disabled={!canGoNext}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-colors ${
                canGoNext
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Next
              <svg
                className="w-5 h-5"
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
            </button>
          </div>
        )}

        {/* Transition Message */}
        {transitionMessage && (
          <div className="mb-6 bg-green-50 border-l-4 border-green-500 p-4 rounded-r-lg">
            <div className="flex items-center">
              <svg
                className="w-6 h-6 text-green-500 mr-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
              <p className="text-green-800 font-medium">{transitionMessage}</p>
            </div>
          </div>
        )}

        {/* Journey Progress */}
        <div className="mb-8">
          <JourneyProgress
            currentStage={displayStage.stage_id}
            stageName={displayStage.stage_name}
            visitNumber={displayStage.visit_number}
          />
        </div>

        {/* Questions */}
        {displayStage.questions.length > 0 ? (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900">
              Stage Questions ({displayStage.questions.length})
            </h2>

            {/* All Questions */}
            {displayStage.questions.map((question) => (
              <QuestionCard
                key={question.id}
                question={question}
                onSubmit={handleAnswerSubmit}
                isViewingPrevious={isViewingPrevious}
              />
            ))}

            {/* Continue Button - only show for current stage */}
            {!isViewingPrevious && (
              <div className="mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={handleContinue}
                  disabled={!allQuestionsAnswered || loading}
                  className={`w-full py-4 px-6 rounded-lg font-semibold text-lg transition-all ${
                    allQuestionsAnswered && !loading
                      ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-lg'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-60'
                  }`}
                >
                  {loading ? 'Processing...' : allQuestionsAnswered ? 'Continue →' : 'Answer all questions to continue'}
                </button>
                {!allQuestionsAnswered && (
                  <p className="text-sm text-gray-500 text-center mt-2">
                    {journey.questions.filter(q => q.previous_answer !== undefined).length} of {journey.questions.length} answered
                  </p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="card text-center">
            <svg
              className="w-16 h-16 text-gray-400 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No Questions Available
            </h3>
            <p className="text-gray-600">
              You've completed all questions for this stage. Your journey may have concluded.
            </p>
          </div>
        )}

        {/* Journey Info */}
        <div className="mt-8 card bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Journey Information</h3>
          <dl className="text-sm space-y-1">
            <div className="flex justify-between">
              <dt className="text-gray-600">Started:</dt>
              <dd className="text-gray-900">
                {new Date(journey.journey_started_at).toLocaleString()}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">Last Updated:</dt>
              <dd className="text-gray-900">
                {new Date(journey.last_updated_at).toLocaleString()}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">User ID:</dt>
              <dd className="text-gray-900 font-mono text-xs">{journey.user_id}</dd>
            </div>
          </dl>
        </div>
      </main>
    </div>
  );
}
