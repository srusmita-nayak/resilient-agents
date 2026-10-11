import React from 'react';
import { NavLink } from 'react-router-dom';
import { Shield, Activity, Cpu, Layers, BarChart2, History, BookOpen, Wifi, WifiOff } from 'lucide-react';
import { HealthStatus } from '../api/types';

interface HeaderProps {
  health: HealthStatus | null;
  wsConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ health, wsConnected }) => {
  const isHealthy = health?.status === 'healthy';

  const navItems = [
    { to: '/', label: 'Overview', icon: Activity },
    { to: '/workspace', label: 'Workspace', icon: Layers },
    { to: '/lab', label: 'Experiment Lab', icon: Cpu },
    { to: '/inspector', label: 'Middleware Inspector', icon: Shield },
    { to: '/analytics', label: 'Research Analytics', icon: BarChart2 },
    { to: '/history', label: 'History', icon: History },
    { to: '/architecture', label: 'Protocol Docs', icon: BookOpen },
  ];

  return (
    <header className="border-b border-lab-800 bg-lab-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Info */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-accent-blue/10 border border-accent-blue/30 flex items-center justify-center text-accent-blue">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base tracking-wide text-white">RESILIENT AGENTS</span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-lab-800 border border-lab-700 text-lab-300">
                  v{health?.version || '1.0.0'}
                </span>
              </div>
              <p className="text-[11px] text-lab-400 hidden sm:block">Fault-Tolerant Multi-Agent Coordination Research</p>
            </div>
          </div>

          {/* System Indicators */}
          <div className="flex items-center space-x-3 text-xs">
            {/* Backend Status */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-lab-850 border border-lab-750">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-accent-emerald animate-pulse' : 'bg-accent-rose'}`} />
              <span className="text-lab-300 font-mono text-[11px]">{isHealthy ? 'API Active' : 'API Offline'}</span>
            </div>

            {/* WebSocket Status */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-lab-850 border border-lab-750">
              {wsConnected ? (
                <>
                  <Wifi className="w-3 h-3 text-accent-emerald" />
                  <span className="text-lab-300 font-mono text-[11px]">WS Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-accent-amber" />
                  <span className="text-lab-400 font-mono text-[11px]">WS Reconnecting</span>
                </>
              )}
            </div>

            {/* LLM Key Status Indicator */}
            <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-lab-850 border border-lab-750 text-lab-300">
              <span className="text-[11px] font-mono">
                {health?.llm_configured ? (
                  <span className="text-accent-blue">LLM Ready</span>
                ) : (
                  <span className="text-lab-400">Deterministic Mode</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Bar */}
        <nav className="flex space-x-1 overflow-x-auto py-1 scrollbar-none border-t border-lab-850">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center space-x-2 px-3 py-2 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                  isActive
                    ? 'bg-lab-800 text-white border-b-2 border-accent-blue'
                    : 'text-lab-400 hover:text-lab-200 hover:bg-lab-850/60'
                }`
              }
            >
              <item.icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
};
