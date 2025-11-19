/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";
import HomePage from "../../app/page";

// Mock the Layout component
jest.mock("../../components/Layout", () => {
  return function MockLayout() {
    return <div data-testid="layout">Layout Component</div>;
  };
});

describe("HomePage", () => {
  test("renders Layout component", () => {
    render(<HomePage />);
    expect(screen.getByTestId("layout")).toBeInTheDocument();
    expect(screen.getByText("Layout Component")).toBeInTheDocument();
  });

  test("renders without errors", () => {
    const { container } = render(<HomePage />);
    expect(container).toBeTruthy();
    expect(container.firstChild).not.toBeNull();
  });
});

