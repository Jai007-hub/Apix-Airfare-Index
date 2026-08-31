import { useEffect, useState } from "react";

/* Two clauses, because width alone gets a phone wrong.
 *
 *   1. Anything narrow is a phone.
 *   2. A big phone turned sideways is 932px wide -- past any sensible width
 *      breakpoint -- but it is still a phone. A coarse pointer (touch, no
 *      mouse) in a short viewport catches those without catching a laptop
 *      (fine pointer) or a tablet in landscape (tall enough to clear 540px).
 */
const QUERY = "(max-width: 860px), (pointer: coarse) and (max-height: 540px)";

/** True on a phone -- the device that gets the traveller view rather than the
 *  analyst dashboard. */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(QUERY);
    const onChange = () => setIsMobile(mql.matches);
    // Fires on rotation too, not just resize.
    mql.addEventListener("change", onChange);
    // The media query can already have flipped between first render and this
    // effect (a rotation during hydration), so re-sync rather than assume.
    onChange();
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}
