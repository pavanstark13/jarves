interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  icon?: React.ReactNode;
  type?: 'button' | 'submit';
}

export function Button({ children, onClick, variant = 'primary', size = 'md', disabled, icon, type = 'button' }: ButtonProps) {
  const styles = {
    primary: { background: '#4a9eff', color: '#fff', border: '1px solid #4a9eff' },
    secondary: { background: 'rgba(74,158,255,0.1)', color: '#4a9eff', border: '1px solid rgba(74,158,255,0.3)' },
    danger: { background: 'rgba(255,71,87,0.15)', color: '#ff4757', border: '1px solid rgba(255,71,87,0.3)' },
    ghost: { background: 'transparent', color: '#6b6b8a', border: '1px solid #1e1e2e' },
  };
  const sizes = {
    sm: { padding: '6px 12px', fontSize: '12px' },
    md: { padding: '8px 16px', fontSize: '14px' },
    lg: { padding: '12px 24px', fontSize: '16px' },
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles[variant], ...sizes[size],
        borderRadius: '8px', fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1, display: 'inline-flex', alignItems: 'center', gap: '6px',
        transition: 'all 0.2s',
      }}
    >
      {icon && icon}
      {children}
    </button>
  );
}
