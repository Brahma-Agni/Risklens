import * as React from 'react';
import { Input as InputPrimitive } from '@base-ui/react/input';

import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        'h-10 w-full min-w-0 rounded-none border-2 border-black bg-white px-3 py-2 text-base font-medium shadow-[3px_3px_0_#000] outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-bold placeholder:text-neutral-500 focus-visible:bg-[#fff7cc] disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-neutral-200 disabled:opacity-60 aria-invalid:bg-[#ffe1e1] md:text-sm',
        className,
      )}
      {...props}
    />
  );
}

export { Input };
