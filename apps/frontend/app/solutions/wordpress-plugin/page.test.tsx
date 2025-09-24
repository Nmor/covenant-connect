import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import WordPressPluginPage from './page';

describe('WordPressPluginPage', () => {
  it('renders hero content and primary sections', () => {
    render(<WordPressPluginPage />);

    expect(
      screen.getByRole('heading', {
        name: /publish ministry content in minutes/i
      })
    ).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /request download/i })).toHaveAttribute(
      'href',
      'mailto:support@covenantconnect.com?subject=WordPress%20Plugin%20Access'
    );

    expect(screen.getByText(/real-time content sync/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /three steps to launch/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /plugin support/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /frequently asked questions/i })).toBeInTheDocument();
  });
});
