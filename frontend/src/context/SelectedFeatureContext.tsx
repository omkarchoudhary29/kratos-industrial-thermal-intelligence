import React, { createContext, useContext, useState } from 'react';

export type FeatureType = 'observation' | 'cluster' | 'facility' | 'region' | 'report' | 'task';

export type BasemapId = 'satellite' | 'hybrid' | 'street' | 'dark' | 'light' | 'terrain';

export interface SelectedFeature {
  type: FeatureType;
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  regionId?: string | number;
  regionName?: string;
  properties: Record<string, any>;
  association?: {
    nearestFacilityName?: string;
    nearestCategory?: string;
    distanceM?: number;
    relationship?: string;
  };
  timestamp?: string;
}

interface SelectedFeatureContextType {
  selectedFeature: SelectedFeature | null;
  setSelectedFeature: (feature: SelectedFeature | null) => void;
  clearSelectedFeature: () => void;
  isChatOpen: boolean;
  setIsChatOpen: (open: boolean) => void;
  askAIAboutFeature: (feature: SelectedFeature) => void;
  activeBasemap: BasemapId;
  setActiveBasemap: (basemap: BasemapId) => void;
}

const SelectedFeatureContext = createContext<SelectedFeatureContextType | undefined>(undefined);

export const SelectedFeatureProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeBasemap, setActiveBasemap] = useState<BasemapId>('satellite');

  const clearSelectedFeature = () => {
    setSelectedFeature(null);
  };

  const askAIAboutFeature = (feature: SelectedFeature) => {
    setSelectedFeature(feature);
    setIsChatOpen(true);
  };

  return (
    <SelectedFeatureContext.Provider
      value={{
        selectedFeature,
        setSelectedFeature,
        clearSelectedFeature,
        isChatOpen,
        setIsChatOpen,
        askAIAboutFeature,
        activeBasemap,
        setActiveBasemap,
      }}
    >
      {children}
    </SelectedFeatureContext.Provider>
  );
};

export const useSelectedFeature = (): SelectedFeatureContextType => {
  const context = useContext(SelectedFeatureContext);
  if (!context) {
    throw new Error('useSelectedFeature must be used within a SelectedFeatureProvider');
  }
  return context;
};
