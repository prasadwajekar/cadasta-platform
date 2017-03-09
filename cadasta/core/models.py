import itertools
import math
from core.util import slugify
from core.validators import sanitize_string
from django.utils.translation import ugettext as _
from django.db import models
from django.core.exceptions import ValidationError

from .util import random_id, ID_FIELD_LENGTH


class RandomIDModel(models.Model):
    id = models.CharField(primary_key=True, max_length=ID_FIELD_LENGTH)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            kwargs['force_insert'] = True

            ok = False
            while not ok:
                self.id = random_id()

                if not type(self).objects.filter(pk=self.id).exists():
                    ok = True
                    super(RandomIDModel, self).save(*args, **kwargs)

        else:
            super(RandomIDModel, self).save(*args, **kwargs)


class SlugModel:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_slug = self.slug

    def save(self, *args, **kwargs):
        max_length = self._meta.get_field('slug').max_length
        if not self.slug:
            self.slug = slugify(
                self.name, max_length=max_length, allow_unicode=True
            )

        orig_slug = self.slug

        if not self.id or self.__original_slug != self.slug:
            for x in itertools.count(1):
                if not type(self).objects.filter(slug=self.slug).exists():
                    break
                slug_length = max_length - int(math.log10(x)) - 2
                trial_slug = orig_slug[:slug_length]
                self.slug = '{}-{}'.format(trial_slug, x)

        self.__original_slug = self.slug

        return super().save(*args, **kwargs)


class SanitizeFieldsModel:
    INGNORED_NAMES = ['id', 'slug']
    CHECK_FIELDS = (models.TextField, models.CharField)

    def clean_fields(self, exclude=None):
        errors = {}
        if exclude is None:
            exclude = []

        try:
            super().clean_fields(exclude=exclude)
        except ValidationError as e:
            errors = e.error_dict

        for f in self._meta.fields:
            if (f.name in exclude or
                    f.name in self.INGNORED_NAMES or
                    type(f) not in self.CHECK_FIELDS):
                continue

            raw_value = getattr(self, f.attname)
            if not sanitize_string(raw_value):
                if f.name not in errors.keys():
                    errors[f.name] = []

                errors[f.name].append(_("Input can not contain < > ; \\ or /"))

        if errors:
            raise ValidationError(errors)
