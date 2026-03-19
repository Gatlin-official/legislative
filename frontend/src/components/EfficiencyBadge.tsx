// EfficiencyBadge.tsx
// Shows token compression efficiency with color coding

import React from "react";

interface EfficiencyBadgeProps {
  compression_percentage: number;
  tokens_saved: number;
  original_tokens: number;
}

export const EfficiencyBadge: React.FC<EfficiencyBadgeProps> = ({
  compression_percentage,
  tokens_saved,
}) => {
  // Determine color based on efficiency
  let bgColor = "bg-red-100";
  let textColor = "text-red-800";
  let level = "Poor";

  if (compression_percentage >= 50) {
    bgColor = "bg-green-100";
    textColor = "text-green-800";
    level = "Excellent";
  } else if (compression_percentage >= 30) {
    bgColor = "bg-yellow-100";
    textColor = "text-yellow-800";
    level = "Good";
  } else if (compression_percentage >= 15) {
    bgColor = "bg-blue-100";
    textColor = "text-blue-800";
    level = "Fair";
  }

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${bgColor} ${textColor}`}
    >
      <span>{level}</span>
      <span>{compression_percentage.toFixed(1)}%</span>
      <span className="text-xs opacity-75">
        ({tokens_saved} tokens saved)
      </span>
    </div>
  );
};
