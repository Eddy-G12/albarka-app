import React from 'react';
import { twMerge } from 'tailwind-merge';

const BASE =
'h-10 w-full rounded-md border border-albarka-border bg-white px-3 text-sm text-albarka-black placeholder:text-albarka-muted/70 transition-colors duration-150 ease-out hover:border-albarka-black/25 disabled:bg-albarka-bg disabled:text-albarka-muted';

export function Label({
  htmlFor,
  children,
  className




}: {htmlFor?: string;children: React.ReactNode;className?: string;}) {
  return (
    <label
      htmlFor={htmlFor}
      className={twMerge(
        'mb-1.5 block text-2xs font-semibold uppercase tracking-wide text-albarka-muted',
        className
      )}>
      
      {children}
    </label>);

}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={twMerge(BASE, className)} {...props} />;
  }
);

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={twMerge(BASE, 'pr-8', className)} {...props}>
      {children}
    </select>);

  });

export function Champ({
  label,
  htmlFor,
  children,
  className





}: {label: string;htmlFor?: string;children: React.ReactNode;className?: string;}) {
  return (
    <div className={className}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>);

}