/* eslint-disable no-undef, react/prop-types */
const React = require('react');
module.exports = function NextImage({ src, alt, ...props }) {
  return React.createElement('img', { src, alt, ...props });
};
