import React from "react";

type Outcome = string | { title?: string; price?: number } | unknown;

type Snapshot = {
  error?: string;
  question?: string;
  yes_price?: number;
  no_price?: number;
  outcomes?: Outcome[];
  formatted_outcomes?: Outcome[];
  volume?: number;
  liquidity?: number;
};

export default function SnapshotCard({ snapshot }: { snapshot: Snapshot }) {
  return (
    <div
      className="mb-4 rounded-2xl border border-white bg-white/20 shadow-[0_4px_30px_rgba(0,0,0,0.1)] backdrop-blur-[11.3px] p-4"
      style={{ WebkitBackdropFilter: "blur(11.3px)" }}
    >
      <h4 className="text-sm font-medium text-neutral-800 mb-2">Market Snapshot</h4>
      {snapshot.error ? (
        <p className="text-sm text-red-600">{snapshot.error}</p>
      ) : (
        <div className="text-sm text-neutral-700 space-y-2">
          {snapshot.question && (
            <p><span className="font-medium">Question:</span> {snapshot.question}</p>
          )}
          {snapshot.yes_price !== undefined && (
            <div className="space-y-1">
              <p className="font-medium">Current Prices:</p>
              <ul className="list-disc list-inside ml-2 space-y-0.5">
                <li>Yes: {(snapshot.yes_price * 100).toFixed(2)}%</li>
                <li>No: {(snapshot.no_price! * 100).toFixed(2)}%</li>
              </ul>
            </div>
          )}
          {((snapshot.formatted_outcomes && snapshot.formatted_outcomes.length > 0) ||
            (snapshot.outcomes && snapshot.outcomes.length > 0)) && (
            <div>
              <p className="font-medium">Outcomes:</p>
              <ul className="list-disc list-inside ml-2 space-y-0.5">
                {(snapshot.formatted_outcomes || snapshot.outcomes)!.map(
                  (outcome: Outcome, idx: number) => (
                    <li key={idx}>
                      {typeof outcome === "string"
                        ? outcome
                        : typeof outcome === "object" && outcome !== null &&
                          "title" in outcome
                        ? (outcome as { title?: string }).title || String(outcome)
                        : String(outcome)}
                      {typeof outcome === "object" &&
                        outcome !== null &&
                        "price" in outcome &&
                        (outcome as { price?: number }).price !== null &&
                        (outcome as { price?: number }).price !== undefined &&
                        ` (${((outcome as { price: number }).price * 100).toFixed(1)}%)`}
                    </li>
                  ),
                )}
              </ul>
            </div>
          )}
          {snapshot.volume && (
            <p><span className="font-medium">Volume:</span> {snapshot.volume.toLocaleString()} USDC</p>
          )}
          {snapshot.liquidity && (
            <p><span className="font-medium">Liquidity:</span> {snapshot.liquidity.toLocaleString()} USDC</p>
          )}
        </div>
      )}
    </div>
  );
}


