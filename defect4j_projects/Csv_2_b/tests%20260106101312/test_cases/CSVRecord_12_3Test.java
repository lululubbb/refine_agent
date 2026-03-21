package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_12_3Test {

    @Test
    @Timeout(8000)
    void testToString_withNonEmptyValues() throws Exception {
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = "comment";
        long recordNumber = 5L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);

        String expected = "[a, b, c]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToString_withEmptyValues() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);

        String expected = "[]";
        assertEquals(expected, record.toString());
    }

    @Test
    @Timeout(8000)
    void testToString_withNullValuesField() throws Exception {
        // Create instance with valid values
        String[] values = new String[] { "x" };
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 1L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);

        // Use reflection to set private final field values to null to test behavior
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);

        // Remove final modifier from the field to allow modification
        Field modifiersField = Field.class.getDeclaredField("modifiers");
        modifiersField.setAccessible(true);
        modifiersField.setInt(valuesField, valuesField.getModifiers() & ~Modifier.FINAL);

        valuesField.set(record, null);

        // toString will throw NullPointerException if values is null, but let's check that
        try {
            record.toString();
        } catch (NullPointerException e) {
            // expected
            return;
        }
        // Fail if no exception thrown
        throw new AssertionError("Expected NullPointerException when values is null");
    }
}