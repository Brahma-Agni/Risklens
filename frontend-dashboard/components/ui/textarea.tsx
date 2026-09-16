import * as React from 'react';

import { cn } from '@/lib/utils';

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'flex field-sizing-content min-h-24 w-full rounded-none border-2 border-black bg-white px-3 py-2 text-base font-medium shadow-[3px_3px_0_#000] outline-none placeholder:text-neutral-500 focus-visible:bg-[#fff7cc] disabled:cursor-not-allowed disabled:bg-neutral-200 disabled:opacity-60 aria-invalid:bg-[#ffe1e1] md:text-sm',
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
