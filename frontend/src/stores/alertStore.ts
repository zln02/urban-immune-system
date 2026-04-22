/**
 * 선택된 구·경보 표시 토글 등 UI 로컬 상태.
 * API 데이터는 TanStack Query 가 관리. 여기서는 "현재 화면 필터" 만.
 */

import { create } from "zustand";
import type { RiskLevel } from "@/types/alert";

interface AlertStore {
  selectedDistrict: string | null;
  minRiskLevel: RiskLevel;
  showTrainTestSplit: boolean;

  selectDistrict: (code: string | null) => void;
  setMinRiskLevel: (level: RiskLevel) => void;
  toggleTrainTestSplit: () => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  selectedDistrict: null,
  minRiskLevel: "safe",
  showTrainTestSplit: true,

  selectDistrict: (code) => set({ selectedDistrict: code }),
  setMinRiskLevel: (level) => set({ minRiskLevel: level }),
  toggleTrainTestSplit: () =>
    set((s) => ({ showTrainTestSplit: !s.showTrainTestSplit })),
}));
