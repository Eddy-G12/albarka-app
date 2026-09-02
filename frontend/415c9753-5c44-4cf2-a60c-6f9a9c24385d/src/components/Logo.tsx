import React from 'react';

export function Logo({
  taille = 'md',
  sombre = false



}: {taille?: 'sm' | 'md' | 'lg';sombre?: boolean;}) {
  const dimensions = { sm: 26, md: 32, lg: 44 }[taille];
  const titre = { sm: 'text-sm', md: 'text-base', lg: 'text-xl' }[taille];

  return (
    <div className="flex items-center gap-2.5">
      <svg
        width={dimensions}
        height={dimensions}
        viewBox="0 0 48 48"
        role="img"
        aria-label="Logo ALBARKA"
        className="shrink-0">
        
        <rect
          x="24"
          y="2"
          width="31"
          height="31"
          rx="4"
          transform="rotate(45 24 2)"
          fill="#F5A623" />
        
        <path d="M24 13 L33 33 H15 Z" fill={sombre ? '#1A1A1A' : '#1A1A1A'} />
        <rect x="18" y="35" width="12" height="3" rx="1.5" fill="#1A1A1A" />
      </svg>
      <div className="leading-tight">
        <p
          className={`${titre} font-bold tracking-tight ${sombre ? 'text-white' : 'text-albarka-black'}`}>
          
          ALBARKA
        </p>
        <p
          className={`text-[9px] font-medium uppercase tracking-[0.16em] ${
          sombre ? 'text-white/55' : 'text-albarka-muted'}`
          }>
          
          Super Agent Mobile Money
        </p>
      </div>
    </div>);

}