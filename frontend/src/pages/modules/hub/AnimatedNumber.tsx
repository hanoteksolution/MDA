import { useEffect, useMemo, useRef, useState } from "react";
import { formatCurrency } from "@/utils/cn";

interface AnimatedNumberProps {
  value: number;
  money?: boolean;
  integer?: boolean;
  className?: string;
  duration?: number;
}

export function AnimatedNumber({
  value,
  money,
  integer,
  className,
  duration = 700,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);
  const target = Number.isFinite(value) ? value : 0;

  useEffect(() => {
    const from = fromRef.current;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      const next = from + (target - from) * eased;
      setDisplay(next);
      if (t < 1) frame = requestAnimationFrame(tick);
      else fromRef.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  const label = useMemo(() => {
    if (money) return formatCurrency(display);
    if (integer) return Math.round(display).toLocaleString();
    return display.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }, [display, money, integer]);

  return <span className={className}>{label}</span>;
}
