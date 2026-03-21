package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

class CSVRecord_1_4Test {

    @Test
    @Timeout(8000)
    void testConstructorWithNonNullValuesAndMapping() throws Exception {
        String[] values = new String[]{"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "comment";
        long recordNumber = 123L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);

        // Use reflection to check private fields
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        assertArrayEquals(values, (String[]) valuesField.get(csvRecord));

        Field mappingField = CSVRecord.class.getDeclaredField("mapping");
        mappingField.setAccessible(true);
        assertEquals(mapping, mappingField.get(csvRecord));

        Field commentField = CSVRecord.class.getDeclaredField("comment");
        commentField.setAccessible(true);
        assertEquals(comment, commentField.get(csvRecord));

        Field recordNumberField = CSVRecord.class.getDeclaredField("recordNumber");
        recordNumberField.setAccessible(true);
        assertEquals(recordNumber, recordNumberField.getLong(csvRecord));
    }

    @Test
    @Timeout(8000)
    void testConstructorWithNullValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);

        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        String[] internalValues = (String[]) valuesField.get(csvRecord);
        assertNotNull(internalValues);
        assertEquals(0, internalValues.length);

        Field mappingField = CSVRecord.class.getDeclaredField("mapping");
        mappingField.setAccessible(true);
        assertEquals(mapping, mappingField.get(csvRecord));

        Field commentField = CSVRecord.class.getDeclaredField("comment");
        commentField.setAccessible(true);
        assertNull(commentField.get(csvRecord));

        Field recordNumberField = CSVRecord.class.getDeclaredField("recordNumber");
        recordNumberField.setAccessible(true);
        assertEquals(recordNumber, recordNumberField.getLong(csvRecord));
    }
}