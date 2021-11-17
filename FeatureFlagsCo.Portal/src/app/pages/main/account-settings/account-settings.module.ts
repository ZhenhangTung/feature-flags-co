import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AccountSettingsRoutingModule } from './account-settings-routing.module';
import { AccountSettingsComponent } from './account-settings.component';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { ProfileComponent } from './profile/profile.component';
import { AccountComponent } from './account/account.component';
import { TeamComponent } from './team/team.component';
import { ProjectComponent } from './project/project.component';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzMessageModule } from 'ng-zorro-antd/message';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzModalModule  } from 'ng-zorro-antd/modal';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzDescriptionsModule } from 'ng-zorro-antd/descriptions';
import { ShareModule } from 'src/app/share/share.module';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { ProjectFilterPipe } from "./project/project-filter.pipe";

@NgModule({
  declarations: [AccountSettingsComponent, AccountComponent, ProfileComponent, TeamComponent, ProjectComponent, ProjectFilterPipe],
  imports: [
    CommonModule,
    FormsModule,
    ShareModule,
    NzFormModule,
    NzTabsModule,
    NzIconModule,
    NzInputModule,
    NzButtonModule,
    NzMessageModule,
    NzDividerModule,
    NzTypographyModule,
    NzModalModule,
    NzSelectModule,
    NzTableModule,
    NzSpinModule,
    NzCardModule,
    NzDescriptionsModule,
    NzSpaceModule,
    NzPopconfirmModule,
    NzRadioModule,
    ScrollingModule,
    ReactiveFormsModule,
    AccountSettingsRoutingModule
  ]
})
export class AccountSettingsModule { }
