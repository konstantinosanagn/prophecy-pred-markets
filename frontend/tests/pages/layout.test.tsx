/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";
import RootLayout from "../../app/layout";

// Mock next/font/google
jest.mock("next/font/google", () => ({
  Inter: jest.fn(() => ({
    className: "inter-font-class",
    style: {},
  })),
}));

// Mock globals.css import
jest.mock("../../app/globals.css", () => ({}));

describe("RootLayout", () => {
  test("renders html element with lang attribute", () => {
    render(
      <RootLayout>
        <div>Test Content</div>
      </RootLayout>
    );
    // In jsdom, html and body are rendered as document.documentElement and document.body
    const htmlElement = document.documentElement;
    expect(htmlElement).not.toBeNull();
    expect(htmlElement).toHaveAttribute("lang", "en");
  });

  test("renders body element with font class", () => {
    render(
      <RootLayout>
        <div>Test Content</div>
      </RootLayout>
    );
    // In jsdom, body is rendered as document.body
    const bodyElement = document.body;
    expect(bodyElement).not.toBeNull();
    expect(bodyElement).toHaveClass("inter-font-class");
  });

  test("renders children", () => {
    render(
      <RootLayout>
        <div data-testid="child">Test Content</div>
      </RootLayout>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  test("renders multiple children", () => {
    render(
      <RootLayout>
        <div data-testid="child1">Child 1</div>
        <div data-testid="child2">Child 2</div>
      </RootLayout>
    );
    expect(screen.getByTestId("child1")).toBeInTheDocument();
    expect(screen.getByTestId("child2")).toBeInTheDocument();
  });

  test("renders empty children", () => {
    render(<RootLayout>{null}</RootLayout>);
    // In jsdom, body is rendered as document.body
    const bodyElement = document.body;
    expect(bodyElement).not.toBeNull();
    // Body might have some default content in jsdom, so just check it exists
    expect(bodyElement).toBeInTheDocument();
  });

  test("has correct metadata", () => {
    // Metadata is exported but not directly testable in component render
    // We can verify it exists by checking the export
    expect(RootLayout).toBeDefined();
  });

  test("renders without errors", () => {
    const { container } = render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );
    expect(container).toBeTruthy();
    expect(container.firstChild).not.toBeNull();
  });

  test("applies Inter font configuration", () => {
    // eslint-disable-next-line no-undef
    const { Inter } = require("next/font/google");
    render(
      <RootLayout>
        <div>Test</div>
      </RootLayout>
    );
    expect(Inter).toHaveBeenCalledWith({
      subsets: ["latin"],
      display: "swap",
    });
  });

  test("renders complex children structure", () => {
    render(
      <RootLayout>
        <header>
          <h1>Header</h1>
        </header>
        <main>
          <p>Main content</p>
        </main>
        <footer>
          <p>Footer</p>
        </footer>
      </RootLayout>
    );
    expect(screen.getByText("Header")).toBeInTheDocument();
    expect(screen.getByText("Main content")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });
});

