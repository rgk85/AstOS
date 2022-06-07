#!/usr/bin/python3
import os
import time
import sys
import subprocess

# TODO: the installer needs a proper rewrite - in progress

args = list(sys.argv)

def clear():
    os.system("clear")

def to_uuid(part):
    uuid = str(subprocess.check_output(f"blkid -s UUID -o value {part}", shell=True))
    return uuid.replace("b'","").replace('"',"").replace("\\n'","")

def main(args):
    # default pacstrap options
    pacstrapOptionsMandatory = "base btrfs-progs grub python3 python-anytree"
    pacstrapOptionsEfi = ""
    pacstrapOptions = "linux-lts linux-firmware git networkmanager"
    # default btrfs mount options
    btrfsMountOptions = "compress=zstd,noatime"

    # --------------------------------------------------
    # 1.0 Installation selection
    # --------------------------------------------------

    # installation profile
    while True:
        clear()
        #print("Welcome to the astOS installer!\n\n\n\n\n")
        #print("Select installation profile:\n1. Minimal install - suitable for embedded devices or servers\n2. Desktop install (Gnome) - suitable for workstations\n3. Desktop install (KDE Plasma)\n0. Custom Test")
        # installation profile welcome message
        print(f'Welcome to the AstOS installer!\n\n')
        print(f'Select installation profile:')
        print(f'1. Minimal install - suitable for embedded devices or servers')
        print(f'2. Desktop install (Gnome) - suitable for workstations')
        print(f'3. Desktop install (KDE Plasma)')
        print(f'0. Advanced install - your choice of installation\n\n')
        # capture input        
        installationProfile = str(input("> "))
        print(installationProfile)
        if installationProfile == "1":
            desktopInstall = 0
            break
        if installationProfile == "2":
            desktopInstall = 1
            break
        if installationProfile == "3":
            desktopInstall = 2
            break
        if installationProfile == "0":
            desktopInstall = 0
            break

    # installationProfile 0 - begin
    if installationProfile == "0":
        # set pacstrap packages
        while True:
            clear()
            # pactrap welcome message
            print(f'Base Packages.\n\n')
            print(f'Some mandatory packages are included by default, they're necessary for astOS to function.')
            print(f'Value: {pacstrapOptionsMandatory}\n\n')
            print(f'Default packages, you can override those here if you wish to do so.')
            print(f'Value: {pacstrapOptions}\n\n')           
            # capture input 
            pacstrapInput = str(input("> "))
            # check for actual input before overriding default
            if pacstrapInput:
                pacstrapOptions = pacstrapInput
                break

        # set btrfs mount options
        while True:
            clear()
            # btrfs mount options welcome message
            print(f'BTRFS Mount Options.\n\n')
            print(f'Default btrfs mount options.')
            print(f'Value: {btrfsMountOptions}\n\n')
            # capture input
            btrfsInput = str(input("> "))
            # check for actual input before overriding default
            if btrfsInput:
                btrfsMountOptions = btrfsInput
                break
    # installationProfile 0 - end


    # --------------------------------------------------
    # 1.1 Installation preparation
    # - installation media update
    # - disk preparation
    # - btrfs structure
    # - os information
    # --------------------------------------------------

    # update pacman and installation
    os.system("pacman -S --noconfirm archlinux-keyring")
    os.system("pacman --noconfirm -Sy")
    
    # set btrfs format on root partition
    os.system(f"mkfs.btrfs -f {args[1]}")
    
    # check for efi partition
    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False
    
    # mount root partition
    os.system(f"mount {args[1]} /mnt")
    
    # btrfs directories - the order of the values must be aligned, mounting will be incorrect if not.
    btrfsDirectories = ["@","@.snapshots","@home","@var","@etc","@boot"]
    mountDirectories = ["",".snapshots","home","var","etc","boot"]
   
    # create all btrfs directories in /mnt
    for btrfsDirectory in btrfsDirectories:
        os.system(f"btrfs sub create /mnt/{btrfsDirectory}")
    
    # unmount /mnt
    os.system(f"umount /mnt")
    
    # mount root partition using btrfs
    os.system(f"mount {args[1]} -o subvol=@,{btrfsMountOptions} /mnt")
    
    # create additional directories
    os.system("mkdir /mnt/{boot,etc,var}")
    
    # mount additional directories using btrfs
    for mountDirectory in mountDirectories:
        os.system(f"mkdir /mnt/{mountDirectory}")
        os.system(f"mount {args[1]} -o subvol={btrfsDirectories[mountDirectories.index(mountDirectory)]},{btrfsMountOptions} /mnt/{mountDirectory}")
    
    # create sub folder structure 
    os.system("mkdir -p /mnt/{tmp,root}")
    os.system("mkdir -p /mnt/.snapshots/{rootfs,etc,var,boot,tmp,root}")

    # create efi directory and mount (if we're using that), include efibootmgr in our initial package installation
    if efi:
        os.system("mkdir /mnt/boot/efi")
        os.system(f"mount {args[3]} /mnt/boot/efi")
        pacstrapOptionsEfi = "efibootmgr"
   
    # pacstrap, initial package installation
    os.system(f"pacstrap /mnt {pacstrapOptionsMandatory} {pacstrapOptions} {pacstrapOptionsEfi}")
    
    # add btrfs configuration to fstab
    os.system(f"echo 'UUID=\"{to_uuid(args[1])}\" / btrfs subvol=@,{btrfsMountOptions},ro 0 0' > /mnt/etc/fstab")
    # add all subvolumnes
    for mountDirectory in mountDirectories:
        os.system(f"echo 'UUID=\"{to_uuid(args[1])}\" /{mountDirectory} btrfs subvol=@{mountDirectory},{btrfsMountOptions} 0 0' >> /mnt/etc/fstab")
    # add efi 
    if efi:
        os.system(f"echo 'UUID=\"{to_uuid(args[3])}\" /boot/efi vfat umask=0077 0 2' >> /mnt/etc/fstab")

    # ast configuration
    os.system("echo '/.snapshots/ast/root /root none bind 0 0' >> /mnt/etc/fstab")
    os.system("echo '/.snapshots/ast/tmp /tmp none bind 0 0' >> /mnt/etc/fstab")
    astpart = to_uuid(args[1])
    os.system(f"mkdir -p /mnt/usr/share/ast/db")
    os.system(f"echo '0' > /mnt/usr/share/ast/snap")
    os.system("mkdir /mnt/etc/astpk.d")
    os.system(f"echo '{args[1]}' > /mnt/etc/astpk.d/astpk-part")
    os.system(f"echo '0' > /mnt/etc/astpk.d/astpk-csnapshot")
    os.system(f"echo '0' > /mnt/etc/astpk.d/astpk-cetc")
    os.system(f"mkdir /mnt/usr/share/ast")
    os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast")
    os.system(f"sed -i s,\"#DBPath      = /var/lib/pacman/\",\"DBPath      = /usr/share/ast/\",g /mnt/etc/pacman.conf")

    # os information
    os.system(f"echo 'NAME=\"astOS\"' > /mnt/etc/os-release")
    os.system(f"echo 'PRETTY_NAME=\"astOS\"' >> /mnt/etc/os-release")
    os.system(f"echo 'ID=astos' >> /mnt/etc/os-release")
    os.system(f"echo 'BUILD_ID=rolling' >> /mnt/etc/os-release")
    os.system(f"echo 'ANSI_COLOR=\"38;2;23;147;209\"' >> /mnt/etc/os-release")
    os.system(f"echo 'HOME_URL=\"https://github.com/astos\"' >> /mnt/etc/os-release")
    os.system(f"echo 'LOGO=astos-logo' >> /mnt/etc/os-release")
    os.system(f"echo 'DISTRIB_ID=\"astOS\"' > /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_RELEASE=\"rolling\"' >> /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_DESCRIPTION=astOS' >> /mnt/etc/lsb-release")
      
    # --------------------------------------------------
    # 1.2 Post installation 
    # - user(s) configuration
    # - locale
    # - keyboard layout
    # - hostname
    # --------------------------------------------------

    # default post installation values
    timezoneOption = "Europe"
    localeOption = "en_DK.UTF-8 UTF-8"
    keyboardOption = ""
    hostnameOption = "astOS"

    # timezone configuration
    while True:
        clear()
        # timezone welcome message
        print(f'Timezone.\n\n')
        print(f'Input desired timezone, if you're unsure type list to list all available.')
        print(f'Default: {timezoneOption}\n\n')
        # capture input
        timezoneInput = input("> ")
        # validate input
        if timezoneInput == "list":
            os.system("ls /usr/share/zoneinfo | less")
        elif timezoneInput:
            timezoneOption = str(f"/usr/share/zoneinfo/{timezoneInput}")
            break
        else:
            break
    
    # locale configuration
    while True:
        clear()
        # locale welcome message
        print(f'Locale.\n\n')
        print(f'Input desired locale, if you're unsure type list to list all available.')
        print(f'Default: {localeOption}\n\n')
        # capture input
        localeInput = input("> ")
        # validate input
        if localeInput == "list":
            os.system("cat /etc/locale.gen | less")
        elif localeInput:
            localeOption = localeInput
        else:
            break

    # hostname configuration
    while True:
        clear()
        # locale welcome message
        print(f'Hostname.\n\n')
        print(f'Input desired hostname.')
        print(f'Default: {hostnameOption}\n\n')
        # capture input
        hostnameInput = input("> ")
        if hostnameInput:
            hostnameOption = hostnameInput
            break
 
    clear()
    # root password welcome message
    print(f'Root password.\n\n')    
    print(f'Input root password.\n\n')    
    # set root password
    os.system("arch-chroot /mnt passwd")
    # root password configuration
    while True:
        # root password welcome message
        print(f'Was root password set successfully (y/n)?\n\n')       
        # capture input
        rootPasswordInput = input("> ")
        # validate input
        if rootPasswordInput.casefold() == "y":
            break
        else:
            os.system("arch-chroot /mnt passwd")


    # additional command
    while True:
        clear()
        # additional command welcome message
        print(f'Do you wish do make additional changes?\n\n')
        print(f'You have to specify exact commands, all commands target your /mnt per default.\n\n')
        # capture input
        additionalCommandInput = input("> ")
        # validate input
        if additionalCommandInput.casefold() == "y":
            # capture input
            commandInput  = input("> ")
            # validate input
            if commandInput:
                os.system(f"arch-chroot /mnt {commandInput}")
        else:
            break
   
    # services to enable
    # os.system("arch-chroot /mnt systemctl enable NetworkManager")

    # --------------------------------------------------
    # 1.3 Post installation 
    # - apply all post installation configurations
    # --------------------------------------------------

    # apply timezone configuration
    os.system(f"arch-chroot /mnt ln -sf {timezoneOption} /etc/localtime")

    # apply locale configuration
    os.system(f"echo '{localeOption}' >> /mnt/etc/locale.gen")
    os.system(f"arch-chroot /mnt locale-gen")
    os.system(f"echo 'LANG={localeOption}' > /mnt/etc/locale.conf")

    # apply hostname configuration
    os.system(f"echo {hostnameOption} > /mnt/etc/hostname")

    # additional post installation configuration, no user interaction needed.
    os.system(f"arch-chroot /mnt hwclock --systohc")

    # apply fstab post installation configuration
    os.system("sed -i '0,/@/{s,@,@.snapshots/rootfs/snapshot-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@etc/{s,@etc,@.snapshots/etc/etc-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@boot/{s,@boot,@.snapshots/boot/boot-tmp,}' /mnt/etc/fstab")

    # initial default snapshot tree configuration
    os.system("mkdir -p /mnt/var/astpk")
    os.system("mkdir -p /mnt/.snapshots/{ast,boot,etc,rootfs,var}")
    os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'}]} > /mnt/.snapshots/ast/fstree")

    # grub installation and configuration
    os.system(f"arch-chroot /mnt sed -i s,Arch,AstOS,g /etc/default/grub")
    os.system(f"arch-chroot /mnt grub-install {args[2]}")
    os.system(f"arch-chroot /mnt grub-mkconfig {args[2]} -o /boot/grub/grub.cfg")
    os.system("sed -i '0,/subvol=@/{s,subvol=@,subvol=@.snapshots/snapshot-tmp,g}' /mnt/boot/grub/grub.cfg")

    # ast tool configuration (copy and make executable)
    os.system("cp ./astpk.py /mnt/usr/local/sbin/ast")
    os.system("arch-chroot /mnt chmod +x /usr/local/sbin/ast")

    # btrfs post installation configuration 
    # take first "root" snapshot, this will be the foundation for all future clones
    os.system("mkdir -p /mnt/root/images")
    os.system("arch-chroot /mnt btrfs sub set-default /.snapshots/rootfs/snapshot-tmp")
    os.system("arch-chroot /mnt ln -s /.snapshots/ast /var/lib/ast")
    # take initial snapshot 
    os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-0")
    # create additional subvolumes
    os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
    # create pacman and systemd directories in subvolumes    
    os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
    # copy to tmp pacman and systemd directories
    os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
    os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
    os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
    # take snapshots of var, etc and boot
    os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-0")
    os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-0")
    os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-0")
    # add to ast configuration
    os.system(f"echo '{astpart}' > /mnt/.snapshots/ast/part")

    # --------------------------------------------------
    # 1.4 Desktop installation 
    # - run installation for a given desktop environment
    # --------------------------------------------------

    # add new snapshot tree if desktop is required
    if desktopInstall:
        os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'},{\\'name\\': \\'1\\'}]} > /mnt/.snapshots/ast/fstree")
        os.system(f"echo '{astpart}' > /mnt/.snapshots/ast/part")
   # desktop specific installation
    if desktopInstall == "2":
        DesktopGnome()
    elif desktopInstall == "3":
        DesktopKde()
    else:
        os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-0 /mnt/.snapshots/rootfs/snapshot-tmp")

    # --------------------------------------------------
    # 1.5 Installation cleanup
    # - unount
    # - copy to snapshots
    # --------------------------------------------------

    # copy and empty root and tmp
    os.system("cp -r /mnt/root/. /mnt/.snapshots/root/")
    os.system("cp -r /mnt/tmp/. /mnt/.snapshots/tmp/")
    os.system("rm -rf /mnt/root/*")
    os.system("rm -rf /mnt/tmp/*")

    # unmount /boot/efi
    if efi:
        os.system("umount /mnt/boot/efi")

    # unmount /mnt/boot and cleanup
    os.system("umount /mnt/boot")
    os.system(f"mount {args[1]} -o subvol=@boot,{btrfsMountOptions} /mnt/.snapshots/boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-tmp/* /mnt/boot")
    # unmount /mnt/etc and cleanup
    os.system("umount /mnt/etc") 
    os.system(f"mount {args[1]} -o subvol=@etc,{btrfsMountOptions} /mnt/.snapshots/etc/etc-tmp")
    os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-tmp/* /mnt/etc")

    # copy to snapshot-tmp (snapshot number determined by desktopInstall value)
    if desktopInstall:
        os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-1/* /mnt/.snapshots/rootfs/snapshot-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.snapshots/var/var-1/* /mnt/.snapshots/rootfs/snapshot-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-1/* /mnt/.snapshots/rootfs/snapshot-tmp/boot")
    else:
        os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-0/* /mnt/.snapshots/rootfs/snapshot-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.snapshots/var/var-0/* /mnt/.snapshots/rootfs/snapshot-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-0/* /mnt/.snapshots/rootfs/snapshot-tmp/boot")

    # unmount /mnt
    os.system("umount -R /mnt")
    # mount root partition
    os.system(f"mount {args[1]} /mnt")
    # delete subvolume
    os.system("btrfs sub del /mnt/@")
    # unmount /mnt
    os.system("umount -R /mnt")

    # installation complete message
    clear()
    print(f'Installation complete.')
    print(f'You can reboot now :)')
    
    
def DesktopGnome():
    os.system(f"echo '1' > /mnt/usr/share/ast/snap")
    os.system("pacstrap /mnt flatpak gnome gnome-extra gnome-themes-extra gdm pipewire pipewire-pulse sudo")
    clear()
    print("Enter username (all lowercase, max 8 letters)")
    username = input("> ")
    while True:
        print("did your set username properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            clear()
            print("Enter username (all lowercase, max 8 letters)")
            username = input("> ")
    os.system(f"arch-chroot /mnt useradd {username}")
    os.system(f"arch-chroot /mnt passwd {username}")
    while True:
        print("did your password set properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            clear()
            os.system(f"arch-chroot /mnt passwd {username}")
    os.system(f"arch-chroot /mnt usermod -aG audio,input,video,wheel {username}")
    os.system(f"arch-chroot /mnt passwd -l root")
    os.system(f"chmod +w /mnt/etc/sudoers")
    os.system(f"echo '%wheel ALL=(ALL:ALL) ALL' >> /mnt/etc/sudoers")
    os.system(f"chmod -w /mnt/etc/sudoers")
    os.system(f"arch-chroot /mnt mkdir /home/{username}")
    os.system(f"echo 'export XDG_RUNTIME_DIR=\"/run/user/1000\"' >> /home/{username}/.bashrc")
    os.system(f"arch-chroot /mnt chown -R {username} /home/{username}")
    os.system(f"arch-chroot /mnt systemctl enable gdm")
    os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast/db")
    os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-1")
    os.system("btrfs sub del /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub del /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub del /mnt/.snapshots/boot/boot-tmp")
    os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
    os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
    os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
    os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
    os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-1")
    os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-1")
    os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-1")
    os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-1 /mnt/.snapshots/rootfs/snapshot-tmp")


def DesktopKde():
    os.system(f"echo '1' > /mnt/usr/share/ast/snap")
    os.system("pacstrap /mnt flatpak plasma xorg kde-applications sddm pipewire pipewire-pulse sudo")
    clear()
    print("Enter username (all lowercase, max 8 letters)")
    username = input("> ")
    while True:
        print("did your set username properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            clear()
            print("Enter username (all lowercase, max 8 letters)")
            username = input("> ")
    os.system(f"arch-chroot /mnt useradd {username}")
    os.system(f"arch-chroot /mnt passwd {username}")
    while True:
        print("did your password set properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            clear()
            os.system(f"arch-chroot /mnt passwd {username}")
    os.system(f"arch-chroot /mnt usermod -aG audio,input,video,wheel {username}")
    os.system(f"arch-chroot /mnt passwd -l root")
    os.system(f"chmod +w /mnt/etc/sudoers")
    os.system(f"echo '%wheel ALL=(ALL:ALL) ALL' >> /mnt/etc/sudoers")
    os.system(f"echo '[Theme]' > /mnt/etc/sddm.conf")
    os.system(f"echo 'Current=breeze' >> /mnt/etc/sddm.conf")
    os.system(f"chmod -w /mnt/etc/sudoers")
    os.system(f"arch-chroot /mnt mkdir /home/{username}")
    os.system(f"echo 'export XDG_RUNTIME_DIR=\"/run/user/1000\"' >> /home/{username}/.bashrc")
    os.system(f"arch-chroot /mnt chown -R {username} /home/{username}")
    os.system(f"arch-chroot /mnt systemctl enable sddm")
    os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast/db")
    os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-1")
    os.system("btrfs sub del /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub del /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub del /mnt/.snapshots/boot/boot-tmp")
    os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
    os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
    os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
    os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
    os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-1")
    os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-1")
    os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-1")
    os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-1 /mnt/.snapshots/rootfs/snapshot-tmp")


main(args)
