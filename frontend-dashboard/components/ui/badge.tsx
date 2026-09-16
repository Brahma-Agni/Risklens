import { mergeProps } from '@base-ui/react/merge-props';
import { useRender } from '@base-ui/react/use-render';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'group/badge inline-flex min-h-6 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-full border-2 border-black px-2.5 py-0.5 text-[.68rem] font-extrabold tracking-[.06em] whitespace-nowrap uppercase transition-all focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 [&>svg]:pointer-events-none [&>svg]:size-3!',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground [a]:hover:bg-[#ff8585]',
        secondary:
          'bg-secondary text-secondary-foreground [a]:hover:bg-[#ffe36b]',
        destructive: 'bg-[#ff6b6b] text-black [a]:hover:bg-[#ff8585]',
        outline: 'bg-white text-black [a]:hover:bg-secondary',
        ghost:
          'border-transparent bg-transparent hover:border-black hover:bg-white',
        link: 'text-primary underline-offset-4 hover:underline',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

function Badge({
  className,
  variant = 'default',
  render,
  ...props
}: useRender.ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: 'span',
    props: mergeProps<'span'>(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props,
    ),
    render,
    state: {
      slot: 'badge',
      variant,
    },
  });
}

export { Badge, badgeVariants };
