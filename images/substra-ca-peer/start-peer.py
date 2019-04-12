# There are really two "types" of MSPs:
#
# An MSP which is used as a signing identity
# For the default MSP type (X509-based), the signing identity uses the crypto material in the keystore (private key) and
# signcerts (X509 public key which matches the keystore private key). Peers and orderers use their "local MSP" for
# signing; examples would be peers signing endorsement responses and orderers signing blocks (deliver responses)
#
# An MSP which is used to verify signatures / identities
# In this case, when a node needs to verify the signature (e.g. a peer verifying the signature of an endorsement
# proposal from a client), it will extract the MSPID from the creator field in the message it receives, look to see if
#  t has a copy of the MSP for that MSPID.
#
# If the role requires MEMBER, it then uses the "cacerts" / "intermediatecerts" content to verify that the identity was
# indeed issued by that MSP. It then uses the public key which is also in the creator field to validate the signature.
#
# In the case where an ADMIN role is required, it actually checks to make sure that the creator public key is an exact
# match for one of the X509 public certs in the "admincerts" folder.
#
# NOTE: There is technically no difference between an "admin" cert and a "member" cert. An identity becomes an "ADMIN"
#  role by simply adding the public certificate to the "admincerts" folder of the MSP.
#
# NOTE: The MSPs for all members of a channel are distributed to all the peers that are part of a channel via config
# blocks. The orderer also has the MSPs for all members of each channel / consortium as well.

from subprocess import call

if __name__ == '__main__':
    call(['peer', 'node', 'start'])
