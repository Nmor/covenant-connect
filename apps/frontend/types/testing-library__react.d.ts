import type { ReactElement } from 'react';

declare module '@testing-library/react' {
  export type RenderResult = {
    container: HTMLElement;
    rerender: (ui: ReactElement) => void;
    unmount: () => void;
  };

  export const screen: {
    getByRole: (role: string, options?: Record<string, unknown>) => HTMLElement;
    getByText: (text: string | RegExp, options?: Record<string, unknown>) => HTMLElement;
    getAllByText: (text: string | RegExp, options?: Record<string, unknown>) => HTMLElement[];
  };

  export function render(ui: ReactElement): RenderResult;
}
