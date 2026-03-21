package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_7_1Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[] { "a", "b", "c" };
        mapping = mock(Map.class);
        comment = "comment";
        recordNumber = 123L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        // Cast array to Object to avoid varargs ambiguity
        csvRecord = constructor.newInstance((Object) values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    void testIterator_returnsIteratorOverValues() {
        Iterator<String> iterator = csvRecord.iterator();
        assertNotNull(iterator);

        // Collect elements from iterator and verify they match values array
        String[] iterated = new String[values.length];
        int i = 0;
        while (iterator.hasNext()) {
            iterated[i++] = iterator.next();
        }
        assertArrayEquals(values, iterated);
    }

    @Test
    @Timeout(8000)
    void testIterator_emptyValuesArray() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord emptyRecord = constructor.newInstance((Object) new String[0], mapping, comment, recordNumber);

        Iterator<String> iterator = emptyRecord.iterator();
        assertNotNull(iterator);
        assertFalse(iterator.hasNext());
    }

    @Test
    @Timeout(8000)
    void testIterator_reflectiveAccess_privateValuesField() throws Exception {
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        Object fieldValue = valuesField.get(csvRecord);
        assertTrue(fieldValue instanceof String[]);
        assertArrayEquals(values, (String[]) fieldValue);
    }
}