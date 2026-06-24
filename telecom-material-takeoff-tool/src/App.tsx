/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DashboardOverview from './components/DashboardOverview';
import DesignCenter from './components/DesignCenter';

export default function App() {
  const [activeView, setActiveView] = useState<string>('dashboard');
  const [selectedSystemId, setSelectedSystemId] = useState<string>('paga');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  
  // Load initial checklist progress from localStorage
  const [checklistState, setChecklistState] = useState<{ [sysId: string]: { [itemId: string]: boolean } }>(() => {
    try {
      const saved = localStorage.getItem('telecom_checklist_progress');
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      console.error("Failed to parse checklist progress from localStorage", e);
      return {};
    }
  });

  // Save checklist progress to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('telecom_checklist_progress', JSON.stringify(checklistState));
  }, [checklistState]);

  const handleToggleChecklistItem = (systemId: string, itemId: string) => {
    setChecklistState(prev => {
      const sysState = prev[systemId] || {};
      return {
        ...prev,
        [systemId]: {
          ...sysState,
          [itemId]: !sysState[itemId]
        }
      };
    });
  };

  return (
    <div className="w-screen h-screen overflow-hidden bg-[#0b0f19] flex m-0 p-0 font-sans antialiased text-slate-200">
      {/* Collapsible Navigation Sidebar */}
      <Sidebar 
        activeView={activeView} 
        setActiveView={setActiveView} 
        collapsed={sidebarCollapsed} 
        setCollapsed={setSidebarCollapsed} 
      />

      {/* Main Content Window */}
      <div className="flex-grow h-screen flex flex-col overflow-hidden relative">
        
        {/* Render View Layer */}
        {activeView === 'dashboard' && (
          <DashboardOverview 
            checklistState={checklistState} 
            setActiveView={setActiveView} 
            setSelectedSystemId={setSelectedSystemId} 
          />
        )}

        {activeView === 'takeoff' && (
          <iframe 
            src="/takeoff_tool.html" 
            className="w-full h-full border-none flex-grow" 
            title="Telecom Material Takeoff Tool"
          />
        )}

        {/* Design Center View Group */}
        {(activeView === 'guide' || activeView === 'checklist' || activeView === 'calculator' || activeView === 'diagram') && (
          <DesignCenter 
            checklistState={checklistState} 
            onToggleChecklistItem={handleToggleChecklistItem} 
            selectedSystemId={selectedSystemId} 
            setSelectedSystemId={setSelectedSystemId}
            activeView={activeView}
          />
        )}
      </div>
    </div>
  );
}
