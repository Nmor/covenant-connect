import React from 'react';

const RANGE_OPTIONS = [
  { value: '30d', label: 'Last 30 days' },
  { value: '60d', label: 'Last 60 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: '6m', label: 'Last 6 months' },
  { value: '1y', label: 'Last 12 months' }
] as const;

type TimeRangeFilterProps = {
  selected?: string;
};

export default function TimeRangeFilter({ selected }: TimeRangeFilterProps): JSX.Element {
  return (
    <form className="flex flex-wrap items-end gap-3" method="get">
      <label className="flex flex-col text-sm font-medium text-slate-700">
        <span>Reporting window</span>
        <select
          className="mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
          defaultValue={selected ?? '90d'}
          name="range"
        >
          {RANGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <button
        className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
        type="submit"
      >
        Apply
      </button>
    </form>
  );
}
