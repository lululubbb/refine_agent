package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_7_3Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    public void setUp() throws Exception {
        values = new String[] { "val1", "val2", "val3" };
        mapping = mock(Map.class);
        comment = "comment";
        recordNumber = 123L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testIteratorReturnsCorrectValues() {
        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);

        int index = 0;
        while (iterator.hasNext()) {
            String val = iterator.next();
            assertEquals(values[index], val);
            index++;
        }
        assertEquals(values.length, index);
    }

    @Test
    @Timeout(8000)
    public void testIteratorOnEmptyValuesArray() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord emptyRecord = constructor.newInstance(new String[0], mapping, comment, recordNumber);

        Iterator<String> iterator = emptyRecord.iterator();
        assertNotNull(iterator);
        assertFalse(iterator.hasNext());
    }

    @Test
    @Timeout(8000)
    public void testIteratorReflectiveAccessToValuesField() throws Exception {
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        String[] internalValues = (String[]) valuesField.get(csvRecord);
        assertArrayEquals(values, internalValues);

        Iterator<String> iterator = csvRecord.iterator();
        int i = 0;
        while (iterator.hasNext()) {
            assertEquals(internalValues[i], iterator.next());
            i++;
        }
        assertEquals(internalValues.length, i);
    }
}