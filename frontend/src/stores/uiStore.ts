import { create } from "zustand";

type ResultViewMode = "table" | "cards" | "compare";
type ResultTab = "overview" | "skills" | "followups";

interface UIState {
  resultViewMode: ResultViewMode;
  resultTab: ResultTab;
  leftPanelCollapsed: boolean;
  rightPanelCollapsed: boolean;
  sessionSearchQuery: string;

  setResultViewMode: (mode: ResultViewMode) => void;
  setResultTab: (tab: ResultTab) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  setSessionSearchQuery: (query: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  resultViewMode: "table",
  resultTab: "overview",
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  sessionSearchQuery: "",

  setResultViewMode: (mode) => set({ resultViewMode: mode }),
  setResultTab: (tab) => set({ resultTab: tab }),
  toggleLeftPanel: () =>
    set((state) => ({ leftPanelCollapsed: !state.leftPanelCollapsed })),
  toggleRightPanel: () =>
    set((state) => ({ rightPanelCollapsed: !state.rightPanelCollapsed })),
  setSessionSearchQuery: (query) => set({ sessionSearchQuery: query }),
}));
