# TypeScript in React Applications

## What is TypeScript?

TypeScript is a strongly typed programming language that builds on JavaScript. It adds static type definitions to JavaScript, which helps catch errors during development rather than at runtime.

## Benefits of TypeScript

- **Type Safety**: Catch errors at compile time instead of runtime
- **Better IDE Support**: Enhanced autocomplete, navigation, and refactoring
- **Self-Documenting Code**: Types serve as documentation
- **Improved Maintainability**: Makes code more predictable, especially in large codebases
- **Enhanced Developer Experience**: Better tooling and editor support

## TypeScript in Your React Project

Your project is configured with TypeScript via Create React App's TypeScript template. Key configuration points:

- TypeScript configuration in `tsconfig.json`
- React component types from `@types/react` package
- Type definitions for Jest in testing files

## Key TypeScript Features for React Development

### Type Annotations

```typescript
// Variable typing
const count: number = 0;
const title: string = "Hello";
const isActive: boolean = true;

// Function parameter and return types
function add(a: number, b: number): number {
  return a + b;
}
```

### Interfaces & Types

```typescript
// Interface for component props
interface ButtonProps {
  text: string;
  onClick: () => void;
  disabled?: boolean; // Optional property
}

// Type for component props (alternative)
type CardProps = {
  title: string;
  content: string;
  imageUrl?: string;
};

// React component with typed props
const Button: React.FC<ButtonProps> = ({ text, onClick, disabled }) => {
  return (
    <button onClick={onClick} disabled={disabled}>
      {text}
    </button>
  );
};
```

### React Hooks with TypeScript

```typescript
// useState with type inference
const [count, setCount] = useState(0); // TypeScript infers number

// useState with explicit typing
const [user, setUser] = useState<User | null>(null);

// useRef with typing
const inputRef = useRef<HTMLInputElement>(null);

// Event handling with typed events
const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
  console.log(event.target.value);
};
```

### Type Assertions

```typescript
// Type assertion when you know more about a type than TypeScript does
const element = document.getElementById('root') as HTMLElement;

// Alternative syntax (less common in React projects)
const element = <HTMLElement>document.getElementById('root');
```

## Best Practices

1. **Avoid using `any`** - It defeats the purpose of TypeScript
2. **Create interfaces for component props** - Improves documentation and type safety
3. **Use TypeScript with React hooks** - Provides better type inference
4. **Extend existing types** - Don't reinvent the wheel
5. **Use union types for props that can take multiple types** - Increases flexibility while maintaining type safety

## TypeScript Resources

- [TypeScript Official Documentation](https://www.typescriptlang.org/docs/)
- [React TypeScript Cheatsheet](https://github.com/typescript-cheatsheets/react)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
