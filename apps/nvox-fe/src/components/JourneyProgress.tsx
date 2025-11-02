interface JourneyProgressProps {
  currentStage: string;
  stageName: string;
  visitNumber: number;
}

export function JourneyProgress({ currentStage, stageName, visitNumber }: JourneyProgressProps) {
  return (
    <div className="card bg-gradient-to-r from-primary-500 to-primary-600 text-white">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold mb-1">{stageName}</h2>
          <p className="text-primary-100">Stage: {currentStage}</p>
          <p className="text-primary-100 text-sm mt-1">Visit #{visitNumber}</p>
        </div>
        <div className="bg-white/20 rounded-full p-4">
          <svg
            className="w-12 h-12"
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
        </div>
      </div>
    </div>
  );
}
