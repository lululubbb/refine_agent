package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_7_4Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[]{"value1", "value2", "value3"};
        mapping = mock(Map.class);
        comment = "comment";
        recordNumber = 5L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    void testIterator() {
        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);

        // Check all values are iterated in order
        int index = 0;
        while (iterator.hasNext()) {
            assertEquals(values[index], iterator.next());
            index++;
        }
        assertEquals(values.length, index);
    }

    @Test
    @Timeout(8000)
    void testIterator_emptyValues() throws Exception {
        // Create CSVRecord with empty values array
        String[] emptyValues = new String[0];
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord emptyRecord = constructor.newInstance(emptyValues, mapping, comment, recordNumber);

        Iterator<String> iterator = emptyRecord.iterator();
        assertNotNull(iterator);
        assertFalse(iterator.hasNext());
    }

    @Test
    @Timeout(8000)
    void testIterator_valuesFieldReflectively() throws Exception {
        // Change values field reflectively to test iterator reflects changes
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        String[] newValues = new String[]{"a", "b"};

        // Remove final modifier from the field
        Field modifiersField = Field.class.getDeclaredField("modifiers");
        modifiersField.setAccessible(true);
        modifiersField.setInt(valuesField, valuesField.getModifiers() & ~Modifier.FINAL);

        valuesField.set(csvRecord, newValues);

        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);

        int idx = 0;
        while (iterator.hasNext()) {
            assertEquals(newValues[idx], iterator.next());
            idx++;
        }
        assertEquals(newValues.length, idx);
    }
}