{
  description = "A very basic flake";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixos-22.11;
  inputs.flake-utils.url = github:numtide/flake-utils;

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: 
      let
        local_overlays = self: super: {
          cairo = super.cairo.overrideAttrs (oldAttrs: {
            version = "1.17.4";
            src = builtins.fetchurl {
              url = "https://cairographics.org/snapshots/${oldAttrs.pname}-${self.cairo.version}.tar.xz";
              sha256 = "01cpjl0p8y7slqvx52kdcyw46h9zqhkkp6hpk5sfifrnshg4rckl";
            };
            patches = [];
          });
        };
        getSystemPackages = system:
          import nixpkgs {
            overlays = [ local_overlays ];
            inherit system;
          };
        pkgs = getSystemPackages system;

      in {
        devShells.default = with pkgs; mkShell {
          venvDir = "venv";
          nativeBuildInputs = [
          ];
          buildInputs = [
            imagemagick
            gnumake
            python39Packages.python
            python39Packages.venvShellHook
            gobject-introspection
            gtk3
            gst_all_1.gstreamer
            python39Packages.pygobject3
            python39Packages.gst-python
            python39Packages.pycairo
            cairo

            # packages
            python39Packages.numpy
            python39Packages.pillow
            python39Packages.pytest
            python39Packages.pytest-cov
            python39Packages.mock
            python39Packages.sphinx
            #python39Packages.sphinx-rtd-theme

          ];
        };
      });
}
