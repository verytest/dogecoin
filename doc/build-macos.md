### Building dogecoin-qt 1.14 on Intel (x86_64) macs. ###

Tested on OSX 10.11 El Capitan, 10.13 High Sierra and 11.3 Big Sur.

### Clone dogecoin locally, or check it out, etc. ###

```sh
git clone https://github.com/dogecoin/dogecoin.git
```

### Set up OSX basic build dependencies. ##

Install xcode-select commandline utils.

```sh
xcode-select --install
```

**NOTE:** If you have Xcode installed, simply zip it up and move it for this
process, as your current Xcode install will likely conflict. Unzip it back
later.

Make sure frameworks dir is properly owned...

```sh
sudo mkdir /usr/local/Frameworks
sudo chown $(whoami):admin /usr/local/Frameworks
```

Install Brew. (If you already have Brew installed, perform a 'brew update'.)

```sh
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Install dependencies via Brew.

```sh
brew install autoconf automake libtool miniupnpc openssl pkg-config protobuf \
             qt5 zeromq qrencode librsvg boost
```

### Get, Patch And Compile BDB 5.3 ###

Download BDB 5.3.28 source from Oracle.

```sh
curl -o db-5.3.28.tar.gz http://download.oracle.com/berkeley-db/db-5.3.28.tar.gz
tar xvfz db-5.3.28.tar.gz
cd db-5.3.28
```

Build BDB 5.3.28

```sh
cd ../..
cd build_unix

../dist/configure CXX=clang++ --enable-cxx
make

sudo mkdir /usr/local/BerkeleyDB.5.3
sudo chown $(whoami):admin /usr/local/BerkeleyDB.5.3

sudo make install
```

### Set some environment variables and links for bdb and openssl ###

```sh
export LDFLAGS=-L/usr/local/BerkeleyDB.5.3/lib
export CPPFLAGS=-I/usr/local/BerkeleyDB.5.3/include
```

  _**NOTE:** for MacOS BigSur (11.1) or later, and possibly Catalina (10.15) you
  will also have to include the "OBJC_OLD_DISPATCH_PROTOTYPES=1" flag._

  _So in this case you want the above export to be:_

```sh    
export CPPFLAGS="-I/usr/local/BerkeleyDB.5.3/include -DOBJC_OLD_DISPATCH_PROTOTYPES=1"
```

  _(Note that the quotes are required.)_

```sh
export INCPATHS=-I/usr/local/opt/openssl/include
export LIBPATHS=-L/usr/local/opt/openssl/lib
cd /usr/local/include
ln -s ../opt/openssl/include/openssl
```

### Go back to your Dogecoin repo ###

```sh
cd ~/dogecoin

./autogen.sh
./configure --with-gui=qt5 --with-qrcode=yes
make
```

Go have a beverage.

```sh
make install
```

Go have another beverage.

Run it.

```sh
/usr/local/bin/dogecoin-qt
```
