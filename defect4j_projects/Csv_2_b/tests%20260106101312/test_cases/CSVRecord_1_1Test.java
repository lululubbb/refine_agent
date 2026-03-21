package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import org.apache.commons.csv.CSVRecord;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CSVRecord_1_1Test {

    @Test
    @Timeout(8000)
    void testCSVRecordConstructorAndMethods() throws Exception {
        // Prepare test data
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "This is a comment";
        long recordNumber = 123L;

        // Use reflection to get the constructor (package-private)
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);

        // Instantiate CSVRecord
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        // Test get(int)
        assertEquals("value1", record.get(0));
        assertEquals("value2", record.get(1));
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> record.get(2));

        // Test get(String)
        assertEquals("value1", record.get("col1"));
        assertEquals("value2", record.get("col2"));
        assertThrows(IllegalArgumentException.class, () -> record.get("col3"));
        assertThrows(IllegalArgumentException.class, () -> record.get(null));

        // Test isConsistent()
        assertTrue(record.isConsistent());

        // Create inconsistent record for testing isConsistent()
        String[] inconsistentValues = new String[]{"onlyOneValue"};
        CSVRecord inconsistentRecord = constructor.newInstance((Object) inconsistentValues, mapping, null, 1L);
        assertFalse(inconsistentRecord.isConsistent());

        // Test isMapped(String)
        assertTrue(record.isMapped("col1"));
        assertFalse(record.isMapped("col3"));
        assertFalse(record.isMapped(null));

        // Test isSet(String)
        assertTrue(record.isSet("col1"));
        assertFalse(record.isSet("col3"));
        assertFalse(record.isSet(null));

        // Test iterator()
        Iterator<String> iterator = record.iterator();
        assertTrue(iterator.hasNext());
        assertEquals("value1", iterator.next());
        assertEquals("value2", iterator.next());
        assertFalse(iterator.hasNext());

        // Test values() - package-private method, use reflection
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] returnedValues = (String[]) valuesMethod.invoke(record);
        assertArrayEquals(values, returnedValues);

        // Test getComment()
        assertEquals(comment, record.getComment());

        // Test getRecordNumber()
        assertEquals(recordNumber, record.getRecordNumber());

        // Test size()
        assertEquals(values.length, record.size());

        // Test toString()
        String toStringResult = record.toString();
        assertNotNull(toStringResult);
        assertTrue(toStringResult.contains("value1"));
        assertTrue(toStringResult.contains("value2"));
    }

    @Test
    @Timeout(8000)
    void testCSVRecordConstructorWithNullValues() throws Exception {
        // null values array should result in EMPTY_STRING_ARRAY usage internally
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 0L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);

        // Cast null to Object to avoid ambiguity in varargs constructor call
        CSVRecord record = constructor.newInstance((Object) null, mapping, comment, recordNumber);

        assertEquals(0, record.size());
        assertFalse(record.iterator().hasNext());
        assertNull(record.getComment());
        assertEquals(recordNumber, record.getRecordNumber());
    }
}