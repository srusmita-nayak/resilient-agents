import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Header } from '../src/components/Header';
import { ArchitecturePage } from '../src/pages/ArchitecturePage';

describe('Frontend UI Suite', () => {
  it('renders Header with title, system indicator and navigation links', () => {
    const healthMock = {
      status: 'healthy',
      version: '1.0.0',
      database: 'sqlite_wal_active',
      llm_configured: false,
    };

    render(
      <BrowserRouter>
        <Header health={healthMock} wsConnected={true} />
      </BrowserRouter>
    );

    expect(screen.getByText('RESILIENT AGENTS')).toBeInTheDocument();
    expect(screen.getByText('API Active')).toBeInTheDocument();
    expect(screen.getByText('WS Live')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Experiment Lab')).toBeInTheDocument();
    expect(screen.getByText('Research Analytics')).toBeInTheDocument();
    expect(screen.getByText('Protocol Docs')).toBeInTheDocument();
  });

  it('renders Protocol Docs / Architecture page with specifications and comparison table', () => {
    render(
      <BrowserRouter>
        <ArchitecturePage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Resilient Agents Architecture/i)).toBeInTheDocument();
    expect(screen.getByText(/Comparative Evaluation Matrix/i)).toBeInTheDocument();
    expect(screen.getByText('Strict synchronous barrier')).toBeInTheDocument();
    expect(screen.getByText('Bounded at-least-once attempts')).toBeInTheDocument();
  });
});
