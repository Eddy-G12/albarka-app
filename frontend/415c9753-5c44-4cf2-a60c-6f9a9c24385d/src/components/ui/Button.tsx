import React from 'react';
import { twMerge } from 'tailwind-merge';
import { Loader2Icon } from 'lucide-react';

type Variante = 'primaire' | 'secondaire' | 'fantome' | 'danger';
type Taille = 'sm' | 'md';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  taille?: Taille;
  chargement?: boolean;
  icone?: React.ReactNode;
}

const VARIANTES: Record<Variante, string> = {
  primaire:
  'bg-albarka-yellow text-albarka-black hover:bg-albarka-yellow-dark border border-transparent font-semibold',
  secondaire:
  'bg-white text-albarka-black border border-albarka-border hover:border-albarka-black/30 hover:bg-albarka-bg',
  fantome:
  'bg-transparent text-albarka-muted border border-transparent hover:text-albarka-black hover:bg-albarka-bg',
  danger:
  'bg-white text-[#C0392B] border border-[#F0C8C4] hover:bg-[#FDF3F2] font-medium'
};

const TAILLES: Record<Taille, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2'
};

export function Button({
  variante = 'secondaire',
  taille = 'md',
  chargement = false,
  icone,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || chargement}
      className={twMerge(
        'inline-flex items-center justify-center rounded-md transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTES[variante],
        TAILLES[taille],
        className
      )}
      {...props}>
      
      {chargement ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : icone}
      {children}
    </button>);

}