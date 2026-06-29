import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export function Card({ children, className, style, onClick }: CardProps) {
  return (
    <div
      className={cn(className)}
      onClick={onClick}
      style={{
        background: '#12121a',
        border: '1px solid #1e1e2e',
        borderRadius: '12px',
        padding: '20px',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
