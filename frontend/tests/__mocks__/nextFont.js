/* eslint-disable no-undef */
// Mock for next/font/google
// Export a function that returns a mock font function
module.exports = {
  Courier_Prime: function(config) {
    return function MockFontComponent({ children, ...props }) {
      return children || null;
    };
  },
};
