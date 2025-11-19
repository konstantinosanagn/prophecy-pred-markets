"use client";

import React, { PropsWithChildren } from "react";

import Background from "./Background";


export default function Layout({ children }: PropsWithChildren) {
  // Render only the styled background (no hero content for now).
  return <Background>{children}</Background>;
}

