# IA Showroom - Demo Project

A demo project using React, TypeScript, Vite, and various other libraries for building an interactive application with 3D graphics, voice recognition, and state management.

## Features

- **React**: A JavaScript library for building user interfaces.
- **Vite**: A fast build tool optimized for modern web development.
- **TypeScript**: Typed JavaScript for better code quality and maintainability.
- **Three.js**: A 3D library for creating WebGL scenes.
- **React Three Fiber**: React renderer for Three.js, making 3D content easier to integrate with React components.
- **Jotai**: A minimalistic state management solution for React applications.
- **Tailwind CSS**: A utility-first CSS framework for quickly styling your UI.

## Installation

First, clone the repository and navigate into the project directory:

```bash
git clone git@github.com:diconium/skoda-sales-bot-frontend.git
cd skoda-sales-bot-frontend
```

## Environment Variables

This project may require environment variables to run. Create a `.env` file in the root of your project directory with the following variables (example):

```bash
VITE_BACKEND_URL=
VITE_WEBSOCKET_URL=
VITE_ENVIRONMENT=local | production
```

Make sure you replace the placeholders with actual values. Here are some typical variables you might need:

- `VITE_API_URL`: The base URL for the API you are using.
- `VITE_WEBSOCKET_URL`: The base URL for the websockets you are using.
- `VITE_ANOTHER_KEY`: Any other required environment key.

> Note: Vite requires that environment variables are prefixed with `VITE_` for security reasons.


## To install the dependencies:

I recommend using `yarn` for package management, but you can also use `npm` if you prefer. But first, make sure you have:

- Node.js installed on your machine (latest is fine).
- `yarn` installed globally.
- If you prefer `npm`, you can use it instead of `yarn`. Don't forget to remove the `yarn.lock` file before running `npm install`.



```bash
yarn install
```
or
```bash
npm install
```


## Development

To start the development server:

```bash
yarn dev
```
or
```bash
npm run dev
```

This will start the Vite development server, allowing you to see your changes live.

## Build

To create a production build:

```bash
yarn build
```
or
```bash
npm run build
```

This will compile TypeScript and build the project using Vite.

## Preview

To preview the production build locally:

```bash
yarn preview
```
or
```bash
npm run preview
```

## Linting

To lint your code and ensure it follows best practices:

```bash
yarn lint
```
or
```bash
npm run lint
```

## Updating Azure

Until CI/CD has been set up, to update the frontend container on Azure one need to run 

```az acr build --file Dockerfile --registry acrsalesaidev --image skodabot-frontend .```

## Project Structure

- **src/**: This is where the main application code resides.
    - **components/**: React components for UI and other functionality.
    - **assets/**: Static assets like images, icons, etc.
    - **styles/**: CSS or Tailwind-based styling.
- **public/**: Contains static files like `index.html` for Vite.

## Dependencies

Here’s a breakdown of the main dependencies:

- **React**: ^18.3.1
- **React DOM**: ^18.3.1
- **@react-three/drei**: ^9.114.0 (helper components for Three.js)
- **@react-three/fiber**: ^8.17.8 (React renderer for Three.js)
- **Axios**: ^1.7.7 (HTTP client)
- **Jotai**: ^2.10.0 (state management)
- **Three.js**: ^0.168.0 (3D library)

### Dev Dependencies

- **TypeScript**: ^5.5.3 (for TypeScript support)
- **Vite**: ^5.4.1 (development and build tool)
- **ESLint**: ^9.9.0 (linting)
- **Tailwind CSS**: ^3.4.13 (for styling)

## License

This project is private and not open for public distribution.

