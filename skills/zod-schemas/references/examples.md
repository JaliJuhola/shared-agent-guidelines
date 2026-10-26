# Zod schema examples

## Do
```ts
export const OrderSchema = z.object({
  id: z.string().uuid(),
  totalCents: z.number().int().nonnegative(),
});
export type Order = z.infer<typeof OrderSchema>;
```

## Don't
```ts
interface Order { id: string; total: number } // duplicates the schema and drifts
```

## Handler boundary
```ts
const parsed = CreateOrderRequestSchema.safeParse(req.body);
if (!parsed.success) return toValidationError(parsed.error);
```
