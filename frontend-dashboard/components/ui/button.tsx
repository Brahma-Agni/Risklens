import { Button as ButtonPrimitive } from '@base-ui/react/button';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-none border-2 border-black bg-clip-padding text-xs font-extrabold tracking-[.08em] whitespace-nowrap uppercase shadow-[3px_3px_0_#000] transition-all duration-100 outline-none select-none hover:-translate-y-0.5 hover:shadow-[4px_4px_0_#000] focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 active:not-aria-[haspopup]:translate-x-[3px] active:not-aria-[haspopup]:translate-y-[3px] active:not-aria-[haspopup]:shadow-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-[#ff8585]',
        outline:
          'bg-white text-black hover:bg-secondary aria-expanded:bg-secondary',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-[#ffe36b]',
        ghost:
          'border-transparent bg-transparent shadow-none hover:border-black hover:bg-white hover:shadow-[3px_3px_0_#000] aria-expanded:bg-white',
        destructive: 'bg-[#ff6b6b] text-black hover:bg-[#ff8585]',
        link: 'border-0 bg-transparent text-black shadow-none underline decoration-2 underline-offset-4 hover:text-primary',
      },
      size: {
        default:
          'h-10 gap-2 px-4 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3',
        xs: "h-8 gap-1 px-2 text-[.68rem] [&_svg:not([class*='size-'])]:size-3",
        sm: "h-9 gap-1.5 px-3 text-[.72rem] [&_svg:not([class*='size-'])]:size-3.5",
        lg: 'h-12 gap-2 px-5 text-sm',
        icon: 'size-10',
        'icon-xs': "size-8 [&_svg:not([class*='size-'])]:size-3",
        'icon-sm': 'size-9',
        'icon-lg': 'size-12',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

function Button({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
