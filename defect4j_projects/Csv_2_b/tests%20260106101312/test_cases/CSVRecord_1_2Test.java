package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_1_2Test {

    @Test
    @Timeout(8000)
    void testCSVRecordConstructor_nullValues_emptyArrayAssigned() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        String comment = "comment";
        long recordNumber = 10L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) null, mapping, comment, recordNumber);

        assertNotNull(record);
        assertEquals(comment, record.getComment());
        assertEquals(recordNumber, record.getRecordNumber());
        assertEquals(0, record.size());
        assertFalse(record.isConsistent());
        assertFalse(record.isMapped("header1"));
        assertFalse(record.isSet("header1"));
        assertThrows(IndexOutOfBoundsException.class, () -> record.get(0));
        assertThrows(IllegalArgumentException.class, () -> record.get("header1"));
        assertNotNull(record.iterator());
        assertEquals("CSVRecord [comment=comment, recordNumber=10, values=[]]", record.toString());
    }

    @Test
    @Timeout(8000)
    void testCSVRecordConstructor_nonNullValues() throws Exception {
        String[] values = new String[] {"val1", "val2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        String comment = null;
        long recordNumber = 5L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);

        assertEquals("val1", record.get(0));
        assertEquals("val2", record.get(1));
        assertEquals("val1", record.get("header1"));
        assertEquals("val2", record.get("header2"));
        assertNull(record.getComment());
        assertEquals(5L, record.getRecordNumber());
        assertTrue(record.isConsistent());
        assertTrue(record.isMapped("header1"));
        assertTrue(record.isMapped("header2"));
        assertTrue(record.isSet("header1"));
        assertTrue(record.isSet("header2"));
        assertEquals(2, record.size());
        assertNotNull(record.iterator());
        assertEquals("CSVRecord [comment=null, recordNumber=5, values=[val1, val2]]", record.toString());
    }

    @Test
    @Timeout(8000)
    void testCSVRecordConstructor_emptyMapping() throws Exception {
        String[] values = new String[] {"val1"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = "c";
        long recordNumber = 1L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);

        assertEquals("val1", record.get(0));
        assertThrows(IllegalArgumentException.class, () -> record.get("header1"));
        assertFalse(record.isMapped("header1"));
        assertFalse(record.isSet("header1"));
        assertTrue(record.isConsistent());
        assertEquals(1, record.size());
        assertEquals("c", record.getComment());
        assertEquals(1L, record.getRecordNumber());
    }
}