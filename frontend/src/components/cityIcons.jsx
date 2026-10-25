/** Original line-art city marks — On the Grid–style strokes, not their artwork. */

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 3,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function Svg({ children, className }) {
  return (
    <svg
      viewBox="0 0 120 120"
      className={`h-full w-full ${className || ''}`}
      aria-hidden
      xmlns="http://www.w3.org/2000/svg"
    >
      {children}
    </svg>
  );
}

const PATHS = {
  'New York': (
    <>
      <path {...stroke} d="M28 100 V40 L40 28 H55 V100" />
      <path {...stroke} d="M55 100 V22 H78 V100" />
      <path {...stroke} d="M78 100 V48 H98 V100" />
      <path {...stroke} d="M20 100 H108" />
      <path {...stroke} d="M66 22 V12" />
    </>
  ),
  'Los Angeles': (
    <>
      <path {...stroke} d="M18 78 H102" />
      <path {...stroke} d="M28 78 V52 H48 V78" />
      <path {...stroke} d="M52 78 V38 L62 28 H78 V78" />
      <path {...stroke} d="M82 78 V58 H98 V78" />
      <circle {...stroke} cx="95" cy="28" r="10" />
    </>
  ),
  'San Francisco': (
    <>
      <path {...stroke} d="M12 72 C28 52, 48 88, 60 60 C72 32, 92 78, 108 55" />
      <path {...stroke} d="M20 88 H100" />
      <path {...stroke} d="M36 88 V70 M60 88 V52 M84 88 V66" />
    </>
  ),
  Chicago: (
    <>
      <path {...stroke} d="M30 100 V35 H50 V100" />
      <path {...stroke} d="M54 100 V20 H70 V100" />
      <path {...stroke} d="M74 100 V45 H94 V100" />
      <path {...stroke} d="M22 100 H102" />
      <path {...stroke} d="M54 20 L62 8 L70 20" />
    </>
  ),
  Austin: (
    <>
      <path {...stroke} d="M16 70 C36 58, 50 82, 70 62 C86 48, 96 70, 108 60" />
      <path {...stroke} d="M20 88 H100" />
      <path {...stroke} d="M40 70 V88 M70 62 V88" />
      <path {...stroke} d="M52 40 l8 -16 8 16" />
    </>
  ),
  Miami: (
    <>
      <path {...stroke} d="M18 85 Q60 55 102 85" />
      <path {...stroke} d="M30 85 V50 H45 V85" />
      <path {...stroke} d="M50 85 V40 H70 V85" />
      <path {...stroke} d="M75 85 V55 H95 V85" />
      <circle {...stroke} cx="92" cy="28" r="9" />
    </>
  ),
  Seattle: (
    <path
      {...stroke}
      d="M60 18 L68 48 H92 L72 66 L80 96 L60 78 L40 96 L48 66 L28 48 H52 Z"
    />
  ),
  Boston: (
    <>
      <path {...stroke} d="M20 88 H100" />
      <path {...stroke} d="M28 88 V55 L48 40 H70 L88 55 V88" />
      <path {...stroke} d="M48 40 V28 H70 V40" />
      <path {...stroke} d="M55 28 V18 H63 V28" />
      <path {...stroke} d="M40 88 V70 H58 V88" />
    </>
  ),
  London: (
    <>
      <path {...stroke} d="M36 100 V48 H52 V100" />
      <path {...stroke} d="M52 48 L60 28 L68 48 H84 V100 H36" />
      <circle {...stroke} cx="60" cy="22" r="6" />
      <path {...stroke} d="M44 70 H76 M44 82 H76" />
    </>
  ),
  Paris: (
    <>
      <path
        {...stroke}
        d="M60 12 L68 40 H92 L72 58 L80 88 L60 70 L40 88 L48 58 L28 40 H52 Z"
      />
      <path {...stroke} d="M50 100 H70 V88" />
    </>
  ),
  Berlin: (
    <>
      <path {...stroke} d="M60 100 V28" />
      <path {...stroke} d="M42 40 H78" />
      <circle {...stroke} cx="60" cy="22" r="10" />
      <path {...stroke} d="M36 100 H84" />
      <path {...stroke} d="M48 55 H72 M48 70 H72" />
    </>
  ),
  Amsterdam: (
    <>
      <path {...stroke} d="M60 20 V55" />
      <path {...stroke} d="M30 55 H90" />
      <path {...stroke} d="M38 55 L60 95 L82 55" />
      <path {...stroke} d="M45 55 L60 80 L75 55" />
      <path {...stroke} d="M22 100 H98" />
    </>
  ),
  Barcelona: (
    <>
      <path {...stroke} d="M40 100 V55 L60 20 L80 55 V100" />
      <path {...stroke} d="M48 55 H72" />
      <path {...stroke} d="M52 40 H68" />
      <path {...stroke} d="M44 70 H76 M44 85 H76" />
      <circle {...stroke} cx="88" cy="88" r="10" />
    </>
  ),
  Rome: (
    <>
      <path {...stroke} d="M28 88 H92" />
      <path {...stroke} d="M34 88 V48 Q60 28 86 48 V88" />
      <path {...stroke} d="M46 88 V58 M60 88 V50 M74 88 V58" />
      <path {...stroke} d="M40 48 Q60 36 80 48" />
    </>
  ),
  Lisbon: (
    <>
      <path {...stroke} d="M24 70 L60 30 L96 70" />
      <path {...stroke} d="M36 70 V95 H84 V70" />
      <path {...stroke} d="M48 70 V50 H72 V70" />
      <path {...stroke} d="M20 95 H100" />
    </>
  ),
  Dublin: (
    <>
      <path {...stroke} d="M30 90 V45 H50 V90" />
      <path {...stroke} d="M50 45 L70 25 H88 V90 H30" />
      <path {...stroke} d="M58 90 V60 H78 V90" />
      <path {...stroke} d="M70 25 V15" />
    </>
  ),
  Tokyo: (
    <>
      <path {...stroke} d="M60 15 V100" />
      <path {...stroke} d="M40 35 H80" />
      <path {...stroke} d="M34 55 H86" />
      <path {...stroke} d="M28 75 H92" />
      <path {...stroke} d="M48 15 H72" />
      <circle {...stroke} cx="60" cy="48" r="5" />
    </>
  ),
  Osaka: (
    <>
      <path {...stroke} d="M30 90 L45 50 H75 L90 90 Z" />
      <path {...stroke} d="M45 50 L52 30 H68 L75 50" />
      <path {...stroke} d="M52 30 L58 16 H62 L68 30" />
      <path {...stroke} d="M40 70 H80" />
    </>
  ),
  Seoul: (
    <>
      <path {...stroke} d="M25 85 H95" />
      <path {...stroke} d="M35 85 V50 L60 25 L85 50 V85" />
      <path {...stroke} d="M48 85 V60 H72 V85" />
      <path {...stroke} d="M42 50 H78" />
    </>
  ),
  Singapore: (
    <>
      <path {...stroke} d="M30 90 H90" />
      <path {...stroke} d="M40 90 V55 H55 V90" />
      <path {...stroke} d="M60 90 V40 Q75 28 85 40 V90" />
      <path {...stroke} d="M70 40 Q78 20 88 32" />
    </>
  ),
  Bangkok: (
    <>
      <path
        {...stroke}
        d="M60 15 L66 40 H90 L70 55 L78 85 L60 68 L42 85 L50 55 L30 40 H54 Z"
      />
      <path {...stroke} d="M48 100 H72 V85" />
    </>
  ),
  'Hong Kong': (
    <>
      <path {...stroke} d="M22 88 H98" />
      <path {...stroke} d="M30 88 V50 H48 V88" />
      <path {...stroke} d="M52 88 V30 H72 V88" />
      <path {...stroke} d="M76 88 V58 H96 V88" />
      <path {...stroke} d="M20 50 Q40 35 60 48 Q80 60 100 42" />
    </>
  ),
  Taipei: (
    <>
      <path
        {...stroke}
        d="M60 12 L72 40 H95 L76 58 L84 90 L60 72 L36 90 L44 58 L25 40 H48 Z"
      />
      <path {...stroke} d="M52 100 H68 V90" />
    </>
  ),
  Mumbai: (
    <>
      <path {...stroke} d="M28 95 V50 L45 35 H75 L92 50 V95" />
      <path {...stroke} d="M45 35 V22 H75 V35" />
      <path {...stroke} d="M52 22 V12 H68 V22" />
      <path {...stroke} d="M40 95 V70 H80 V95" />
    </>
  ),
  Delhi: (
    <>
      <path {...stroke} d="M25 88 H95" />
      <path {...stroke} d="M32 88 V55 Q60 30 88 55 V88" />
      <path {...stroke} d="M45 88 V62 M60 88 V55 M75 88 V62" />
      <path {...stroke} d="M40 55 Q60 42 80 55" />
    </>
  ),
  Bengaluru: (
    <>
      <path {...stroke} d="M30 85 H90 V55 H30 Z" />
      <path {...stroke} d="M40 55 V35 H80 V55" />
      <path {...stroke} d="M50 35 V22 H70 V35" />
      <circle {...stroke} cx="60" cy="70" r="8" />
      <path {...stroke} d="M25 95 H95" />
    </>
  ),
  Goa: (
    <>
      <path {...stroke} d="M20 80 Q60 55 100 80" />
      <path {...stroke} d="M35 80 V50 L50 35 H70 L85 50 V80" />
      <path {...stroke} d="M50 35 V22 H70 V35" />
      <circle {...stroke} cx="92" cy="28" r="8" />
    </>
  ),
  Sydney: (
    <>
      <path {...stroke} d="M22 85 Q40 40 58 85" />
      <path {...stroke} d="M48 85 Q66 35 84 85" />
      <path {...stroke} d="M70 85 Q88 50 102 85" />
      <path {...stroke} d="M18 88 H108" />
    </>
  ),
  Melbourne: (
    <>
      <path {...stroke} d="M25 90 H95" />
      <path {...stroke} d="M35 90 V50 H55 V90" />
      <path {...stroke} d="M60 90 V35 L75 25 H90 V90" />
      <path {...stroke} d="M42 50 H48 M70 45 H85" />
      <circle {...stroke} cx="28" cy="30" r="7" />
    </>
  ),
  Auckland: (
    <>
      <path {...stroke} d="M20 75 C40 55, 55 90, 75 60 C88 42, 98 70, 108 58" />
      <path {...stroke} d="M35 90 L50 40 L65 90" />
      <path {...stroke} d="M42 70 H58" />
      <path {...stroke} d="M18 95 H102" />
    </>
  ),
};

export default function CityIcon({ id, className = '' }) {
  const paths = PATHS[id] || (
    <>
      <circle {...stroke} cx="60" cy="60" r="28" />
      <path {...stroke} d="M40 60 H80 M60 40 V80" />
    </>
  );
  return <Svg className={className}>{paths}</Svg>;
}
