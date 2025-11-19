import React from "react";
import { render } from "@testing-library/react";

import Layout from "../components/Layout";


test("renders layout without crashing", () => {
  render(
    <Layout>
      <div>Test</div>
    </Layout>,
  );
});


